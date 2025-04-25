# === import general tools ===
from pathlib import Path
import shutil
import traceback
import logging
import streamlit as st

# === import local modules ===
from utils.text_splitter import get_text_splitter
from utils.file_utils import load_documents, get_knowledge_base_files
from utils.model_utils import get_embedding_model
from config.config import VECTOR_DB_PATH, KNOWLEDGE_BASE_PATH
from utils.file_utils import load_single_document
# === LangChain interface ===
from langchain_community.vectorstores import Chroma as ChromaDB  # ✅ 推荐使用
from langchain.retrievers import EnsembleRetriever

# === Chroma configuration (if you really need Settings) ===
from chromadb.config import Settings
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    allow_reset=True,
    is_persistent=True
)

# === Logger settings ===
logger = logging.getLogger(__name__)




# ==================================================================
# 📊 ensure the vector database folder structure
# ==================================================================
def ensure_vector_db_structure():
    for base_path in [VECTOR_DB_PATH, KNOWLEDGE_BASE_PATH]:
        base_path.mkdir(parents=True, exist_ok=True)

# ==================================================================
# 🌐 manage the global vector database
# ==================================================================
def ensure_global_vectordb():
    """Ensure the global vector database exists and contains all documents"""
    try:
        # 1. get all categories
        categories = [d.name for d in KNOWLEDGE_BASE_PATH.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if not categories:
            logger.warning("[VectorDB] No categories found in knowledge base")
            return False

        # 2. load or create the global vector database
        embedding_model = get_embedding_model()
        if not embedding_model:
            return False

        # 3. create the text splitter
        text_splitter = get_text_splitter()
        
        # 4. iterate through all categories to load documents
        all_docs = []
        for category in categories:
            category_path = KNOWLEDGE_BASE_PATH / category
            if not category_path.exists() or not category_path.is_dir():
                continue
                
            # get all files in the category
            files = [f for f in category_path.iterdir() 
                    if f.is_file() and f.suffix.lower() in ['.pdf', '.docx', '.txt', '.md']]
            
            for file_path in files:
                try:
                    docs = load_single_document(file_path)
                    if docs:
                        # ensure the metadata of the document contains the correct source file path
                        for doc in docs:
                            doc.metadata["source"] = str(file_path)
                        all_docs.extend(docs)
                except Exception as e:
                    logger.warning(f"[VectorDB] Failed to load file {file_path}: {e}")
                    continue

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

def get_vectordb():
    """
    Get the global vector database. If it does not exist, create it first.
    """
    # ensure the global vector database exists
    if not (VECTOR_DB_PATH / "__global__").exists():
        if not ensure_global_vectordb():
            return None

    embedding_model = get_embedding_model()
    if not embedding_model:
        return None

    try:
        return ChromaDB(
            persist_directory=str(VECTOR_DB_PATH / "__global__"),
            embedding_function=embedding_model,
            client_settings=CHROMA_SETTINGS
        )
    except Exception as e:
        logger.error(f"[VectorDB] Failed to load global vectordb: {e}")
        return None

# ==================================================================
# ✅ check if the vector database exists
# ==================================================================
def vector_db_exists(category: str, filename: str) -> bool:
    chroma_path = VECTOR_DB_PATH / category
    if not chroma_path.exists():
        return False

    try:
        db = ChromaDB(
            persist_directory=str(chroma_path),
            embedding_function=get_embedding_model(),
            client_settings=CHROMA_SETTINGS
        )
        return any(filename in doc.metadata.get("source", "") for doc in db.get().get("documents", []))
    except Exception as e:
        logger.warning(f"[VectorDB] Load failed: {e}")
        return False

# ==================================================================
# ➕ vectorize new documents
# ==================================================================
def add_documents_to_vectordb(category: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> bool:
    try:
        docs = load_documents(category)
        if not docs:
            st.warning("The document is empty, please upload first")
            return False

        text_splitter = get_text_splitter(chunk_size, chunk_overlap)
        docs = text_splitter.split_documents(docs)

        vectordb = ChromaDB.from_documents(
            documents=docs,
            embedding=get_embedding_model(),
            collection_name=category,
            persist_directory=str(VECTOR_DB_PATH / category),
            client_settings=CHROMA_SETTINGS
        )

        
        logger.info(f"[VectorDB] Vectorization success for category: {category}")
        return True
    except Exception as e:
        logger.warning(f"[VectorDB] Vectorization failed: {e}")
        st.error(f"[VectorDB] Vectorization failed: {e}")
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
    embedding_model = get_embedding_model()
    if not embedding_model:
        return None

    retrievers = []
    for path in paths:
        chroma_path = Path(KNOWLEDGE_BASE_PATH) / path
        if chroma_path.exists():
            db = ChromaDB(
                persist_directory=str(chroma_path),
                embedding_function=embedding_model,
            )
            retrievers.append(db.as_retriever())

    if not retrievers:
        return None
    if len(retrievers) == 1:
        return retrievers[0]

    return EnsembleRetriever(retrievers=retrievers)

# ==================================================================
# 🔐 load the global matrix
# ==================================================================
def load_all_documents_as_retriever():
    embedding_model = get_embedding_model()
    if not embedding_model:
        return None

    chroma_path = Path(KNOWLEDGE_BASE_PATH) / "__global__"
    if not chroma_path.exists():
        return None

    return ChromaDB(
        persist_directory=str(chroma_path),
        embedding_function=embedding_model
    ).as_retriever()

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

        # 2. text splitting
        text_splitter = get_text_splitter()
        split_docs = text_splitter.split_documents(docs)

        # 3. load the global vector database
        embedding_model = get_embedding_model()
        if not embedding_model:
            return False

        vectordb = ChromaDB(
            persist_directory=str(VECTOR_DB_PATH / "__global__"),
            embedding_function=embedding_model,
            client_settings=CHROMA_SETTINGS
        )

        # 4. add documents
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
def embed_single_file(file_path: Path, category: str) -> bool:
    """
    Embed a single file into the category vector database and the global vector database
    """
    try:
        # 1. load the single document
        docs = load_single_document(file_path)
        if not docs:
            logger.warning(f"[VectorDB] Empty document: {file_path}")
            return False

        # 2. text splitting
        splitter = get_text_splitter()
        docs = splitter.split_documents(docs)

        # 3. load the category vector database
        vectordb = ChromaDB(
            persist_directory=str(VECTOR_DB_PATH / category),
            collection_name=category,
            embedding_function=get_embedding_model(),
            client_settings=CHROMA_SETTINGS,
        )

        # 4. add documents to the category vector database
        vectordb.add_documents(docs)
        vectordb.persist()
        
        # 5. update the global vector database
        update_global_vectordb_with_file(file_path)
        
        logger.info(f"[VectorDB] Embedded and stored file: {file_path}")
        return True

    except Exception as e:
        logger.warning(f"[VectorDB] Failed to embed file {file_path}: {e}")
        return False

# ==================================================================
# rebuild the vector database for the specified files
# ==================================================================    
def rebuild_vectordb_for_files(files: list) -> bool:
    """
    Rebuild the vector database
    Args:
        files: list of (category, filename) tuples
    Returns:
        bool: whether the operation is successful
    """
    try:
        # 1. ensure the directory structure
        ensure_vector_db_structure()
        
        # 2. process files by category
        for category, filename in files:
            file_path = KNOWLEDGE_BASE_PATH / category / filename
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                continue
                
            # 3. embed the single file
            if not embed_single_file(file_path, category):
                logger.warning(f"Failed to embed file: {file_path}")
                continue
                
        logger.info("[VectorDB] Vector database rebuilt successfully")
        return True
        
    except Exception as e:
        logger.error(f"[VectorDB] Failed to rebuild vector database: {e}")
        return False