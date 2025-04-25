from typing import List, Optional
from pathlib import Path
from langchain.vectorstores import Chroma
from langchain.schema import BaseRetriever
from config import KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH
from utils.model_utils import get_embedding_model
from utils.file_utils import save_uploaded_file
from utils.vectordb_utils import embed_single_file, CHROMA_SETTINGS
import logging
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader

def get_embedding_model():
    """Get the embedding model with error handling"""
    try:
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    except Exception as e:
        logging.error(f"Failed to initialize embedding model: {str(e)}")
        raise RuntimeError("Failed to initialize embedding model. Please check if the model is available.")

def get_category_docs_retriever(category: str, selected_files: List[str] = None):
    """Load selected documents under category as retriever"""
    try:
        embedding_model = get_embedding_model()
        
        # Construct path for category's vector db
        vector_db_path = Path(VECTOR_DB_PATH) / category
        vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma with persistent directory
        vectordb = Chroma(
            persist_directory=str(vector_db_path),
            embedding_function=embedding_model,
            client_settings=Settings(
                anonymized_telemetry=False,
                is_persistent=True
            )
        )
        
        # If no documents found, return None
        if vectordb._collection.count() == 0:
            logging.warning(f"No documents found in vector store for category: {category}")
            return None
            
        # Filter documents based on source if files are selected
        if selected_files:
            retriever = vectordb.as_retriever(
                search_kwargs={
                    "filter": {"source": {"$in": selected_files}},
                    "k": 4
                }
            )
        else:
            retriever = vectordb.as_retriever(
                search_kwargs={"k": 4}
            )
            
        return retriever
        
    except Exception as e:
        logging.error(f"Error getting category docs retriever: {str(e)}")
        raise RuntimeError(f"Failed to initialize document retriever: {str(e)}")

def process_uploaded_file(uploaded_file, category: str):
    """Save uploaded file and embed into category vector db"""
    try:
        # Save file
        category_path = Path(KNOWLEDGE_BASE_PATH) / category
        category_path.mkdir(parents=True, exist_ok=True)
        
        file_path = category_path / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # Load document based on file type
        if file_path.suffix.lower() == '.pdf':
            loader = PyPDFLoader(str(file_path))
        else:
            loader = TextLoader(str(file_path))
            
        documents = loader.load()
        
        # Add source metadata
        for doc in documents:
            doc.metadata["source"] = uploaded_file.name
            
        # Get embedding model
        embedding_model = get_embedding_model()
        
        # Initialize/get vector store
        vector_db_path = Path(VECTOR_DB_PATH) / category
        vector_db_path.mkdir(parents=True, exist_ok=True)
        
        vectordb = Chroma(
            persist_directory=str(vector_db_path),
            embedding_function=embedding_model,
            client_settings=Settings(
                anonymized_telemetry=False,
                is_persistent=True
            )
        )
        
        # Add documents to vector store
        vectordb.add_documents(documents)
        vectordb.persist()
        
        logging.info(f"Successfully processed and embedded file: {uploaded_file.name}")
        return True
        
    except Exception as e:
        logging.error(f"Error processing uploaded file: {str(e)}")
        raise RuntimeError(f"Failed to process file {uploaded_file.name}: {str(e)}")

__all__ = [
    "get_category_docs_retriever",
    "process_uploaded_file"
]