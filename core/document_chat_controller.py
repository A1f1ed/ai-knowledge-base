from typing import List, Optional
from pathlib import Path
import logging
import tempfile
import os
import pickle
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import streamlit as st
from services.google_drive_service import GoogleDriveService
from utils.vectordb_utils import embed_single_file

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from chromadb.config import Settings

from config.config import KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH, DRIVE_FOLDER_ID, TOKEN_PATH

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

def initialize_chroma(vector_db_path: Path, embedding_model):
    """Initialize Chroma with proper settings for cloud environment"""
    try:
        # 确保目录存在
        vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # 配置 ChromaDB 设置
        chroma_settings = Settings(
            anonymized_telemetry=False
        )
        
        return Chroma(
            persist_directory=str(vector_db_path),
            embedding_function=embedding_model
        )
    except Exception as e:
        logging.error(f"Failed to initialize Chroma: {str(e)}")
        raise RuntimeError(f"Failed to initialize vector database: {str(e)}")

def get_google_drive_service():
    """Initialize Google Drive service"""
    try:
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Failed to initialize Google Drive service: {str(e)}")
        raise RuntimeError("Failed to initialize Google Drive service")

def sync_vector_store_to_drive(vector_db_path: Path, category: str):
    """Sync vector store to Google Drive"""
    try:
        service = get_google_drive_service()
        
        # 创建一个压缩文件
        import shutil
        archive_path = f"{category}_vector_store.zip"
        shutil.make_archive(f"{category}_vector_store", 'zip', vector_db_path)
        
        # 上传到 Google Drive
        file_metadata = {
            'name': f"{category}_vector_store.zip",
            'parents': [DRIVE_FOLDER_ID]
        }
        
        with open(archive_path, 'rb') as f:
            media = MediaIoBaseUpload(f, mimetype='application/zip')
            # 检查是否已存在同名文件
            results = service.files().list(
                q=f"name='{file_metadata['name']}' and parents='{DRIVE_FOLDER_ID}'",
                fields="files(id)"
            ).execute()
            files = results.get('files', [])
            
            if files:
                # 更新现有文件
                file = service.files().update(
                    fileId=files[0]['id'],
                    media_body=media
                ).execute()
            else:
                # 创建新文件
                file = service.files().create(
                    body=file_metadata,
                    media_body=media
                ).execute()
                
        # 清理临时文件
        os.remove(archive_path)
        
    except Exception as e:
        logging.error(f"Failed to sync vector store to Drive: {str(e)}")
        raise RuntimeError(f"Failed to sync vector store to Drive: {str(e)}")

def load_vector_store_from_drive(category: str) -> Optional[Path]:
    """Load vector store from Google Drive"""
    try:
        service = get_google_drive_service()
        
        # 查找文件
        results = service.files().list(
            q=f"name='{category}_vector_store.zip' and parents='{DRIVE_FOLDER_ID}'",
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])
        
        if not files:
            logging.info(f"No vector store found for category: {category}")
            return None
            
        file_id = files[0]['id']
        
        # 下载文件
        request = service.files().get_media(fileId=file_id)
        vector_store_path = VECTOR_DB_PATH / category
        archive_path = f"{category}_vector_store.zip"
        
        with open(archive_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
        # 解压文件
        import shutil
        vector_store_path.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(archive_path, vector_store_path)
        
        # 清理临时文件
        os.remove(archive_path)
        
        return vector_store_path
        
    except Exception as e:
        logging.error(f"Failed to load vector store from Drive: {str(e)}")
        return None

def get_category_docs_retriever(category: str, selected_files: List[str] = None):
    """Load selected documents under category as retriever"""
    try:
        embedding_model = get_embedding_model()
        vector_db_path = Path(VECTOR_DB_PATH) / category
        
        # 尝试从 Google Drive 加载向量存储
        loaded_path = load_vector_store_from_drive(category)
        if loaded_path:
            vector_db_path = loaded_path
        
        # Initialize Chroma with persistent directory
        vectordb = initialize_chroma(vector_db_path, embedding_model)
        
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
    """
    Process an uploaded file by saving it locally, uploading to Google Drive, and updating the vector database.
    
    Args:
        uploaded_file: The uploaded file
        category: The category path, can include multiple levels (e.g. 'category/subcategory')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # 初始化Google Drive服务
        drive_service = GoogleDriveService()
        
        # 保存到临时文件以进行向量化
        temp_path = Path(save_uploaded_file(uploaded_file, category))
        
        # 上传文件到Google Drive
        file_content = uploaded_file.read()
        upload_status, result = drive_service.upload_file(temp_path, category)
        if not upload_status:
            st.error(f"Failed to upload file to Google Drive: {result}")
            return False
            
        # 向量化文件
        if not embed_single_file(temp_path, category):
            st.error(f"Failed to vectorize file: {uploaded_file.name}")
            return False
            
        return True
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return False

__all__ = [
    "get_category_docs_retriever",
    "process_uploaded_file"
]