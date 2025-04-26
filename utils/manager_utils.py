from config.config import KNOWLEDGE_BASE_PATH
import streamlit as st
from pathlib import Path
import os
import shutil

# ensure the knowledge base structure, optional auto-detection of existing categories.
def ensure_knowledge_base_structure(sync_existing=True):
    """
    Initialize knowledge base structure and sync existing categories.
    
    Args:
        sync_existing (bool): Whether to sync existing folders as categories
    """
    base_path = KNOWLEDGE_BASE_PATH
    base_path.mkdir(parents=True, exist_ok=True)
    
    # 确保 ggbond_knowledge 文件夹存在
    ggbond_path = base_path / 'ggbond_knowledge'
    ggbond_path.mkdir(exist_ok=True)
    
    if sync_existing:
        # 获取 ggbond_knowledge 下的所有子文件夹作为分类
        categories = [
            p.name for p in ggbond_path.iterdir() 
            if p.is_dir() and not p.name.startswith('.')
        ]
        return sorted(categories)
    
    return []

# get the number of files in a category.
def get_file_count(category):
    """Get the number of files in a category"""
    category_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / category
    if not category_path.exists():
        return 0
    return len([f for f in category_path.iterdir() if f.is_file() and not f.name.startswith('.')])

# delete the category and its contents.
def delete_category(category):
    """Delete category and its contents"""
    try:
        category_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / category
        if category_path.exists():
            shutil.rmtree(category_path)
            return True
    except Exception as e:
        st.error(f"删除分类失败: {str(e)}")
        return False

# delete the specified file.
def delete_file(category, filename):
    """Delete specified file"""
    try:
        file_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / category / filename
        if file_path.exists():
            os.remove(file_path)
            return True
    except Exception as e:
        st.error(f"删除文件失败: {str(e)}")
        return False

# rename the category.
def rename_category(old_name, new_name):
    """Rename category"""
    try:
        old_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / old_name
        new_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / new_name
        if old_path.exists() and not new_path.exists():
            old_path.rename(new_path)
            return True
    except Exception as e:
        st.error(f"重命名分类失败: {str(e)}")
        return False

# get file information.
def get_file_info(category, filename):
    """Get file information"""
    file_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / category / filename
    if file_path.exists():
        stats = file_path.stat()
        return {
            'size': stats.st_size,
            'modified': stats.st_mtime,
            'created': stats.st_ctime
        }
    else:
        st.warning(f"找不到文件: {file_path}")
    return None

# get all available category folder names.
def get_available_categories():
    """Get all available category folder names under ggbond_knowledge"""
    ggbond_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge'
    if not ggbond_path.exists():
        ggbond_path.mkdir(parents=True, exist_ok=True)
        return []

    categories = [
        item.name for item in ggbond_path.iterdir()
        if item.is_dir() and not item.name.startswith('.')
    ]
    
    return sorted(categories)

# get the file path list of the specified category.
def get_files_in_category(category: str):
    """Get the file path list of the specified category"""
    category_path = KNOWLEDGE_BASE_PATH / 'ggbond_knowledge' / category
    if not category_path.exists():
        st.warning(f"分类 {category} 不存在")
        return []
        
    files = sorted([f.name for f in category_path.iterdir() if f.is_file() and not f.name.startswith('.')])
    if files:
        st.success(f"在分类 {category} 中找到 {len(files)} 个文件")
    else:
        st.info(f"分类 {category} 中没有文件")
    return files

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
