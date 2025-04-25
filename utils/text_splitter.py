import os
import streamlit as st
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config.config import CHUNK_SIZE, CHUNK_OVERLAP, TEXT_SEPARATORS

# ===================================
# text splitter
# ===================================

def get_text_splitter(file_path=None):
    """
    Automatically select the appropriate text cutting strategy based on the file type.
    Current strategy: long documents / academic papers use more granular cutting.
    """
    try:
        if file_path:
            if _is_academic_document(file_path):
                return RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE // 2,
                    chunk_overlap=CHUNK_OVERLAP // 2,
                    separators=TEXT_SEPARATORS
                )
            elif _is_long_document(file_path):
                return RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    separators=TEXT_SEPARATORS
                )
        # default strategy
        return RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=TEXT_SEPARATORS
        )
    except Exception as e:
        st.error(f"⚠️ failed to load text splitter: {str(e)}")
        return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)


def _is_academic_document(file_path):
    """
    Check if the file is an academic document, based on the file path keywords.
    Can be extended to use content recognition.
    """
    academic_keywords = ["thesis", "paper", "research", "ieee", "acm"]
    file_name = Path(file_path).name.lower()
    return any(keyword in file_name for keyword in academic_keywords)


def _is_long_document(file_path):
    """
    Check if the document is long: currently only judged by file size.
    """
    try:
        size_in_mb = os.path.getsize(file_path) / (1024 * 1024)
        return size_in_mb > 1  # more than 1MB is considered a long document
    except Exception:
        return False

__all__ = ["get_text_splitter"]