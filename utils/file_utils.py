from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
import shutil
from config.config import KNOWLEDGE_BASE_PATH
from pathlib import Path
import logging
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
from typing import Union
logger = logging.getLogger(__name__)

data_base = Path("data_base")

# normalize the path string to a Path object.
def normalize_path(file_path: str) -> Path:
    """
    Normalize the path string to a Path object.
    """
    return Path(file_path).resolve()
# return the corresponding loader based on the file extension.
def get_file_loader(file_path: str):
    """
    Return the corresponding loader based on the file extension.
    """
    path = normalize_path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path))
    elif suffix == ".docx":
        return Docx2txtLoader(str(path))
    elif suffix == ".txt":
        return TextLoader(str(path), autodetect_encoding=True)
    elif suffix == ".md":
        return UnstructuredMarkdownLoader(str(path))
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    
# batch load documents.
def load_documents(file_paths: list) -> list:
    """
    Batch load documents.
    """
    all_docs = []
    for path in file_paths:
        try:
            loader = get_file_loader(path)
            docs = loader.load()
            all_docs.extend(docs)
        except Exception as e:
            logger.warning(f"⚠️ unable to load file {path}: {e}")
    return all_docs

# get all document file paths in the knowledge base directory.
def get_knowledge_base_files() -> list:
    """
    Get all document file paths in the knowledge base directory.
    """
    if not KNOWLEDGE_BASE_PATH.exists():
        return []

    file_extensions = [".pdf", ".docx", ".txt", ".md"]
    return [str(file) for file in KNOWLEDGE_BASE_PATH.rglob("*") if file.suffix.lower() in file_extensions]

# check if the file exists and is of an allowed type.
def is_valid_file(file_path: str) -> bool:
    """
    Check if the file exists and is of an allowed type.
    """
    path = Path(file_path)
    return path.exists() and path.suffix.lower() in [".pdf", ".docx", ".txt", ".md"]

# save uploaded files.
def save_uploaded_files(category: Union[str, list], uploaded_files: list) -> list[Path]:
    # 🛡️ Defensive handling: Ensure category is a string
    if isinstance(category, list):
        category = category[0] if category else "default"

    category_path = Path(KNOWLEDGE_BASE_PATH) / category
    category_path.mkdir(parents=True, exist_ok=True)

    file_paths = []
    for file in uploaded_files:
        file_path = category_path / file.name
        try:
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            file_paths.append(file_path)
        except Exception as e:
            st.error(f"❌ failed to save file {file.name}: {e}")
    return file_paths

# save a single uploaded file.
def save_uploaded_file(uploaded_file, category: str) -> str:
    # Ensure directory exists
    category_path = KNOWLEDGE_BASE_PATH / category
    category_path.mkdir(parents=True, exist_ok=True)

    # Generate file save path
    file_path = category_path / uploaded_file.name

    # Save file content
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(file_path)

# load a single document and return a LangChain document list.
def load_single_document(file_path: Union[str, Path]) -> list:
    """Load a single document and return a LangChain document list"""
    try:
        loader = get_file_loader(str(file_path))
        return loader.load()
    except Exception as e:
        logger.warning(f"⚠️ unable to load single document {file_path}: {e}")
        return []