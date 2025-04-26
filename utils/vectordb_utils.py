# === import general tools ===
from pathlib import Path
import shutil
import traceback
import logging
import streamlit as st
from typing import List, Optional
from functools import lru_cache
import os
import tempfile

# === import local modules ===
from utils.text_splitter import get_text_splitter
from utils.file_utils import load_documents, get_knowledge_base_files, load_single_document, get_file_loader
from utils.model_utils import get_embedding_model
from config.config import VECTOR_DB_PATH, KNOWLEDGE_BASE_PATH
from langchain.schema import Document

# === LangChain interface ===
try:
    from langchain_community.vectorstores import Chroma as ChromaDB
except ImportError:
    # 为了兼容性，尝试旧的导入路径
    from langchain.vectorstores import Chroma as ChromaDB

from langchain.retrievers import EnsembleRetriever
from langchain_community.document_loaders import PyPDFLoader, TextLoader

# === Chroma configuration ===
from chromadb.config import Settings

# Use a temporary directory for cloud environment if needed
TEMP_DIR = tempfile.gettempdir()

# Configure ChromaDB settings for better compatibility
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    allow_reset=True,
    is_persistent=True
)

# === Logger settings ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_chroma_instance(persist_dir: str, embedding_model=None) -> Optional[ChromaDB]:
    """
    Helper function to create a ChromaDB instance with the correct settings
    """
    if embedding_model is None:
        embedding_model = get_embedding_model()
        if not embedding_model:
            return None
            
    try:
        # Ensure the directory exists
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        # Try to create ChromaDB with specified settings
        return ChromaDB(
            persist_directory=persist_dir,
            embedding_function=embedding_model,
            collection_name="default",
            client_settings=CHROMA_SETTINGS
        )
    except Exception as e:
        logger.error(f"[VectorDB] Failed to initialize ChromaDB: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback to temp directory if there's an issue with the specified directory
        try:
            fallback_dir = os.path.join(TEMP_DIR, "chroma_fallback", Path(persist_dir).name)
            Path(fallback_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"[VectorDB] Falling back to temporary directory: {fallback_dir}")
            
            return ChromaDB(
                persist_directory=fallback_dir,
                embedding_function=embedding_model,
                collection_name="default",
                client_settings=CHROMA_SETTINGS
            )
        except Exception as fallback_e:
            logger.error(f"[VectorDB] Fallback also failed: {fallback_e}")
            return None

# ==================================================================
# 📊 ensure the vector database folder structure
# ==================================================================
def ensure_vector_db_structure():
    """
    Ensure the vector database folder structure exists, supporting multi-level directories.
    This function creates the base directories and ensures they have proper permissions.
    """
    try:
        # Create base paths if they don't exist
        for base_path in [VECTOR_DB_PATH, KNOWLEDGE_BASE_PATH]:
            base_path.mkdir(parents=True, exist_ok=True)
            
        # Create global vector store directory
        (VECTOR_DB_PATH / "__global__").mkdir(parents=True, exist_ok=True)
        
        # Mirror the knowledge base directory structure in vector store
        for item in KNOWLEDGE_BASE_PATH.rglob("*"):
            if item.is_dir() and not item.name.startswith('.'):
                relative_path = item.relative_to(KNOWLEDGE_BASE_PATH)
                vector_path = VECTOR_DB_PATH / relative_path
                vector_path.mkdir(parents=True, exist_ok=True)
                
        return True
    except Exception as e:
        logger.error(f"[VectorDB] Failed to ensure vector database structure: {e}")
        return False

# ==================================================================
# 🌐 manage the global vector database
# ==================================================================
def ensure_global_vectordb():
    """Ensure the global vector database exists and contains all documents from all levels of directories"""
    try:
        # 1. get all files recursively from the knowledge base
        if not KNOWLEDGE_BASE_PATH.exists():
            logger.warning("[VectorDB] Knowledge base path does not exist")
            return False

        # 2. load or create the global vector database
        embedding_model = get_embedding_model()
        if not embedding_model:
            return False

        # 3. create the text splitter
        text_splitter = get_text_splitter()
        
        # 4. recursively find and process all documents
        all_docs = []
        
        def process_directory(dir_path: Path):
            for item in dir_path.iterdir():
                if item.name.startswith('.'):
                    continue
                    
                if item.is_file() and item.suffix.lower() in ['.pdf', '.docx', '.txt', '.md']:
                    try:
                        docs = load_single_document(item)
                        if docs:
                            # ensure the metadata of the document contains the correct source file path
                            for doc in docs:
                                doc.metadata["source"] = str(item)
                                # Add relative path for better organization
                                doc.metadata["relative_path"] = str(item.relative_to(KNOWLEDGE_BASE_PATH))
                            all_docs.extend(docs)
                    except Exception as e:
                        logger.warning(f"[VectorDB] Failed to load file {item}: {e}")
                        continue
                elif item.is_dir():
                    process_directory(item)

        # Start recursive processing from the knowledge base root
        process_directory(KNOWLEDGE_BASE_PATH)

        if not all_docs:
            logger.warning("[VectorDB] No valid documents to process")
            return False

        # 5. split the documents
        split_docs = text_splitter.split_documents(all_docs)

        # 6. create or update the global vector database
        global_db = ChromaDB.from_documents(
            documents=split_docs,
            embedding=embedding_model,
            persist_directory=str(VECTOR_DB_PATH / "__global__"),
            client_settings=CHROMA_SETTINGS
        )
        
        logger.info(f"[VectorDB] Global vectordb updated successfully with {len(split_docs)} chunks from {len(all_docs)} documents")
        return True

    except Exception as e:
        logger.error(f"[VectorDB] Failed to ensure global vectordb: {e}")
        st.error(f"Failed to create global vector database: {str(e)}")
        return False

@lru_cache()
def get_vectorstore_client(persist_dir: str) -> Optional[ChromaDB]:
    """
    Get a consistent ChromaDB client with cached embedding model
    
    Args:
        persist_dir: Directory to persist the vector store
        
    Returns:
        ChromaDB instance or None if initialization fails
    """
    try:
        embedding_model = get_embedding_model()
        if not embedding_model:
            raise ValueError("Failed to initialize embedding model")
            
        return ChromaDB(
            persist_directory=persist_dir,
            embedding_function=embedding_model,
            client_settings=CHROMA_SETTINGS
        )
    except Exception as e:
        logger.error(f"[VectorDB] Failed to initialize vector store: {e}")
        return None

def get_vectordb():
    """
    Get the global vector database. If it does not exist, create it first.
    """
    # ensure the global vector database exists
    if not (VECTOR_DB_PATH / "__global__").exists():
        if not ensure_global_vectordb():
            return None
            
    return get_vectorstore_client(str(VECTOR_DB_PATH / "__global__"))

# ==================================================================
# ✅ check if the vector database exists
# ==================================================================
def vector_db_exists(category: str, filename: str) -> bool:
    chroma_path = VECTOR_DB_PATH / category
    if not chroma_path.exists():
        return False

    try:
        db = get_chroma_instance(str(chroma_path))
        if not db:
            return False
        return any(filename in doc.metadata.get("source", "") for doc in db.get().get("documents", []))
    except Exception as e:
        logger.warning(f"[VectorDB] Load failed: {e}")
        return False

# ==================================================================
# ➕ vectorize new documents
# ==================================================================
def add_documents_to_vectordb(documents: List[Document], category: str = None) -> bool:
    """
    Add documents to the vector database, supporting multi-level directory paths.
    
    Args:
        documents (List[Document]): List of documents to add
        category (str, optional): Category path relative to KNOWLEDGE_BASE_PATH. 
                                If None, adds to global vector store.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not documents:
            logger.warning("[VectorDB] No documents provided to add to vector store")
            return True
            
        # Determine the vector store path
        if category:
            # Handle multi-level paths
            category_path = Path(category)
            vector_path = VECTOR_DB_PATH / category_path
        else:
            vector_path = VECTOR_DB_PATH / "__global__"
            
        # Ensure the directory exists
        vector_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize vector store
        vectordb = get_chroma_instance(str(vector_path))
        if not vectordb:
            return False
            
        # Add documents
        vectordb.add_documents(documents)
        vectordb.persist()
        
        logger.info(f"[VectorDB] Successfully added {len(documents)} documents to {vector_path}")
        return True
        
    except Exception as e:
        logger.error(f"[VectorDB] Failed to add documents to vector store: {e}")
        return False

# ==================================================================
#  delete the specified vector database
# ==================================================================
def delete_vector_db(category: str) -> bool:
    db_path = VECTOR_DB_PATH / category
    try:
        if db_path.exists():
            shutil.rmtree(db_path)
        return True
    except Exception as e:
        logger.error(f"[VectorDB] Failed to delete: {e}")
        return False

# ==================================================================
# load the document vector retriever
# ==================================================================
def load_doc_retriever_by_paths(paths: list[str]):
    """
    Load document retrievers for the specified paths, supporting multi-level directory structure
    Args:
        paths: list of paths relative to KNOWLEDGE_BASE_PATH
    Returns:
        A single retriever or an ensemble of retrievers
    """
    retrievers = []
    for path in paths:
        vector_db_path = VECTOR_DB_PATH / path
        if vector_db_path.exists():
            try:
                db = get_chroma_instance(str(vector_db_path))
                if db:
                    retrievers.append(db.as_retriever())
            except Exception as e:
                logger.warning(f"[VectorDB] Failed to load retriever for {path}: {e}")
                continue

    if not retrievers:
        return None
    if len(retrievers) == 1:
        return retrievers[0]

    return EnsembleRetriever(retrievers=retrievers)

# ==================================================================
# 🔐 load the global matrix
# ==================================================================
def load_all_documents_as_retriever():
    """
    Load the global vector database retriever that contains all documents from all directories
    Returns:
        A retriever for the global vector database
    """
    global_db_path = VECTOR_DB_PATH / "__global__"
    if not global_db_path.exists():
        if not ensure_global_vectordb():
            return None

    try:
        db = get_chroma_instance(str(global_db_path))
        if not db:
            return None
        return db.as_retriever()
    except Exception as e:
        logger.error(f"[VectorDB] Failed to load global retriever: {e}")
        return None

__all__ = [
    "ensure_vector_db_structure",
    "get_vectordb",
    "vector_db_exists",
    "add_documents_to_vectordb",
    "delete_vector_db",
    "load_doc_retriever_by_paths",
    "load_all_documents_as_retriever"
]

# ==================================================================
# update the global vector database with a new file
# ==================================================================    
def update_global_vectordb_with_file(file_path: Path) -> bool:
    """
    Add a new file to the global vector database
    """
    try:
        # 1. load the document
        docs = load_single_document(file_path)
        if not docs:
            logger.warning(f"[VectorDB] Empty document: {file_path}")
            return False

        # 2. add metadata including relative path
        for doc in docs:
            doc.metadata["source"] = str(file_path)
            doc.metadata["relative_path"] = str(file_path.relative_to(KNOWLEDGE_BASE_PATH))

        # 3. text splitting
        text_splitter = get_text_splitter()
        split_docs = text_splitter.split_documents(docs)

        # 4. load the global vector database
        embedding_model = get_embedding_model()
        if not embedding_model:
            return False

        vectordb = ChromaDB(
            persist_directory=str(VECTOR_DB_PATH / "__global__"),
            embedding_function=embedding_model,
            client_settings=CHROMA_SETTINGS
        )

        # 5. add documents
        vectordb.add_documents(split_docs)
        vectordb.persist()
        
        logger.info(f"[VectorDB] Added file to global vectordb: {file_path}")
        return True

    except Exception as e:
        logger.error(f"[VectorDB] Failed to update global vectordb with file {file_path}: {e}")
        return False

# ==================================================================
# embed a single file into the category vector database and the global vector database
# ==================================================================
def embed_single_file(file_path: Path, category: str = None) -> bool:
    """
    Embed a single file into vector store, supporting multi-level directory structure
    Args:
        file_path: Path to the file to embed
        category: Optional category path (can include multiple levels) relative to KNOWLEDGE_BASE_PATH
                 If None, it will be derived from file_path's location
    Returns:
        bool: whether the operation is successful
    """
    try:
        from services.google_drive_service import GoogleDriveService
        
        logger.info(f"[VectorDB] Starting embedding process for: {file_path}")
        
        # Get relative path from knowledge base root
        try:
            relative_path = file_path.relative_to(KNOWLEDGE_BASE_PATH)
            # Use provided category or derive from file path
            if category is None:
                category_path = relative_path.parent
            else:
                category_path = Path(category)
            logger.info(f"[VectorDB] Using category path: {category_path}")
        except ValueError as e:
            # If file is not under KNOWLEDGE_BASE_PATH, and no category is provided
            if category is None:
                logger.error(f"[VectorDB] File {file_path} is not under knowledge base path and no category provided")
                return False
            category_path = Path(category)
            relative_path = Path(category) / file_path.name
            logger.info(f"[VectorDB] File outside knowledge base directory, using category: {category}")
            
        # Handle possible errors with vector database path
        try:
            vector_db_path = VECTOR_DB_PATH / category_path
            # Ensure the directory exists
            vector_db_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Fallback to temporary directory if needed
            logger.warning(f"[VectorDB] Error creating vector database path: {str(e)}")
            vector_db_path = Path(os.path.join(TEMP_DIR, "vectordb", str(category_path)))
            vector_db_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"[VectorDB] Using fallback directory: {vector_db_path}")
        
        # Create text splitter
        text_splitter = get_text_splitter()
        
        # Load and process the file
        logger.info(f"[VectorDB] Loading document: {file_path}")
        docs = load_single_document(file_path)
        if not docs:
            logger.warning(f"[VectorDB] Empty document: {file_path}")
            return False
            
        logger.info(f"[VectorDB] Document loaded successfully. Adding metadata...")
        # Add metadata
        for doc in docs:
            doc.metadata["source"] = str(file_path)
            doc.metadata["relative_path"] = str(relative_path)
            doc.metadata["category"] = str(category_path)
            
        # Split documents
        logger.info(f"[VectorDB] Splitting documents...")
        split_docs = text_splitter.split_documents(docs)
        logger.info(f"[VectorDB] Created {len(split_docs)} document chunks")
            
        # Get embedding model
        logger.info(f"[VectorDB] Getting embedding model...")
        embedding_model = get_embedding_model()
        if not embedding_model:
            logger.error("[VectorDB] Failed to get embedding model")
            raise Exception("Failed to get embedding model")
            
        # Create or update vector store
        logger.info(f"[VectorDB] Creating vector store at: {vector_db_path}")
        try:
            # First try with default settings
            vectordb = ChromaDB.from_documents(
                documents=split_docs,
                embedding=embedding_model,
                persist_directory=str(vector_db_path),
                client_settings=CHROMA_SETTINGS
            )
            vectordb.persist()
        except Exception as e:
            # If fails, try with fallback directory
            logger.warning(f"[VectorDB] Error creating vector store: {str(e)}. Trying with fallback...")
            fallback_path = Path(os.path.join(TEMP_DIR, "chroma_fallback", str(category_path).replace("/", "_")))
            fallback_path.mkdir(parents=True, exist_ok=True)
            vectordb = ChromaDB.from_documents(
                documents=split_docs,
                embedding=embedding_model,
                persist_directory=str(fallback_path),
                client_settings=CHROMA_SETTINGS
            )
            vectordb.persist()
            logger.info(f"[VectorDB] Successfully used fallback directory: {fallback_path}")
        
        # Also update global vector store
        logger.info(f"[VectorDB] Updating global vector store...")
        if not update_global_vectordb_with_file(file_path):
            logger.warning(f"[VectorDB] Failed to update global vector store for: {file_path}")
        
        # Sync to Google Drive if needed
        try:
            logger.info(f"[VectorDB] Syncing to Google Drive...")
            drive_service = GoogleDriveService()
            if drive_service.sync_vector_store(str(category_path)):
                logger.info(f"Vector store synced to Drive for path: {category_path}")
            else:
                logger.warning(f"Failed to sync vector store to Drive for path: {category_path}")
        except Exception as e:
            logger.warning(f"[VectorDB] Error syncing to Google Drive: {str(e)}")
        
        logger.info(f"[VectorDB] Successfully embedded file: {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error embedding file {file_path}: {str(e)}")
        logging.error(traceback.format_exc())
        st.error(f"向量化失败: {file_path.name} - {str(e)}")
        return False

# ==================================================================
# rebuild the vector database for the specified files
# ==================================================================    
def rebuild_vectordb_for_files(files: list[Path]) -> bool:
    """
    Rebuild the vector database for the specified files
    Args:
        files: list of Path objects pointing to files to be processed
    Returns:
        bool: whether the operation is successful
    """
    try:
        # 1. ensure the directory structure
        ensure_vector_db_structure()
        
        # 2. process each file
        for file_path in files:
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                continue
                
            # 3. embed the single file
            if not embed_single_file(file_path):
                logger.warning(f"Failed to embed file: {file_path}")
                continue
                
        logger.info("[VectorDB] Vector database rebuilt successfully")
        return True
        
    except Exception as e:
        logger.error(f"[VectorDB] Failed to rebuild vector database: {e}")
        return False

def update_all_categories_to_vectordb() -> bool:
    """
    Update all categories in the knowledge base to the vector database.
    Supports multi-level directory structure.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get all files recursively from knowledge base
        all_files = []
        for file_path in KNOWLEDGE_BASE_PATH.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                all_files.append(file_path)
                
        if not all_files:
            logger.warning("[VectorDB] No files found in knowledge base")
            return True
            
        # Process files by category
        category_files = {}
        for file_path in all_files:
            # Get relative path from KNOWLEDGE_BASE_PATH
            relative_path = file_path.relative_to(KNOWLEDGE_BASE_PATH)
            # Category is the parent directory path
            category = str(relative_path.parent)
            if category == ".":  # Files in root directory
                category = None
                
            if category not in category_files:
                category_files[category] = []
            category_files[category].append(file_path)
            
        # Process each category
        for category, files in category_files.items():
            # Load and split documents
            docs = []
            for file_path in files:
                try:
                    loader = get_file_loader(file_path)
                    if loader:
                        docs.extend(loader.load())
                except Exception as e:
                    logger.error(f"[VectorDB] Failed to load file {file_path}: {e}")
                    continue
                    
            if not docs:
                continue
                
            # Split documents
            text_splitter = get_text_splitter()
            split_docs = text_splitter.split_documents(docs)
            
            # Add to vector store
            success = add_documents_to_vectordb(split_docs, category)
            if not success:
                logger.error(f"[VectorDB] Failed to update category: {category}")
                
        logger.info("[VectorDB] Successfully updated all categories")
        return True
        
    except Exception as e:
        logger.error(f"[VectorDB] Failed to update all categories: {e}")
        return False