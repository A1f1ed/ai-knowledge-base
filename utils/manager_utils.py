from config.config import KNOWLEDGE_BASE_PATH
import streamlit as st
from pathlib import Path
import os
import shutil
BASE_PATH = Path("data_base/knowledge_db")

# ensure the knowledge base structure, optional auto-detection of existing categories.
def ensure_knowledge_base_structure(sync_existing=True):
    """
    Initialize knowledge base structure, optional auto-detection of existing categories.
    
    Args:
        sync_existing (bool): Whether to sync existing folders as categories (including Google Drive / local additions)
    """
    base_path = KNOWLEDGE_BASE_PATH
    base_path.mkdir(parents=True, exist_ok=True)

    # default categories (optional for first use)
    default_categories = [
        'Autobiography', 'history', 'life_weekly',
        'literature', 'society', 'technology'
    ]

    # create default categories (only if they do not exist)
    for category in default_categories:
        category_path = base_path / category
        category_path.mkdir(exist_ok=True)

    # sync existing folders as categories (including local / Drive additions or deletions)
    if sync_existing:
        existing_folders = [
            p.name for p in base_path.iterdir() if p.is_dir() and not p.name.startswith('.')
        ]
        return sorted(existing_folders)

    return default_categories

# get the number of files in a category.
def get_file_count(category):
    """Get the number of files in a category"""
    category_path = KNOWLEDGE_BASE_PATH / category
    if not category_path.exists():
        return 0
    return len([f for f in category_path.iterdir() if f.is_file() and not f.name.startswith('.')])

# delete the category and its contents.
def delete_category(category):
    """Delete category and its contents"""
    try:
        category_path = KNOWLEDGE_BASE_PATH / category
        if category_path.exists():
            shutil.rmtree(category_path)
            return True
    except Exception as e:
        st.error(f"failed to delete category: {str(e)}")
        return False

# delete the specified file.
def delete_file(category, filename):
    """Delete specified file"""
    try:
        file_path = KNOWLEDGE_BASE_PATH / category / filename
        if file_path.exists():
            os.remove(file_path)
            return True
    except Exception as e:
        st.error(f"failed to delete file: {str(e)}")
        return False

# rename the category.
def rename_category(old_name, new_name):
    """Rename category"""
    try:
        old_path = KNOWLEDGE_BASE_PATH / old_name
        new_path = KNOWLEDGE_BASE_PATH / new_name
        if old_path.exists() and not new_path.exists():
            old_path.rename(new_path)
            return True
    except Exception as e:
        st.error(f"failed to rename category: {str(e)}")
        return False

# get file information.
def get_file_info(category, filename):
    """Get file information"""
    file_path = KNOWLEDGE_BASE_PATH / category / filename
    if file_path.exists():
        stats = file_path.stat()
        return {
            'size': stats.st_size,
            'modified': stats.st_mtime,
            'created': stats.st_ctime
        }
    else:
        st.warning(f"file not found: {file_path}")
    return None

# get all available category folder names.
def get_available_categories():
    """Get all available category folder names"""
    if not KNOWLEDGE_BASE_PATH.exists():
        return []

    categories = [
        item.name for item in KNOWLEDGE_BASE_PATH.iterdir()
        if item.is_dir() and not item.name.startswith('.')
    ]
    return sorted(categories)

# get the available category folder names in the knowledge base.
def get_available_categories():
    """Get the available category folder names in the knowledge base"""
    if not BASE_PATH.exists():
        return []
    return sorted([p.name for p in BASE_PATH.iterdir() if p.is_dir()])

# get the file path list of the specified category.
def get_files_in_category(category: str):
    """Get the file path list of the specified category"""
    category_path = KNOWLEDGE_BASE_PATH / category
    if not category_path.exists():
        return []
    return sorted([f.name for f in category_path.iterdir() if f.is_file() and not f.name.startswith('.')])

__all__ = [
    "ensure_knowledge_base_structure",
    "get_file_count",
    "delete_category",
    "delete_file",
    "rename_category",
    "get_file_info",
    "get_available_categories",
    "get_files_in_category",
]
