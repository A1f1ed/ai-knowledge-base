import streamlit as st
from typing import List, Optional
from utils.manager_utils import get_available_categories, get_files_in_category
from utils.file_utils import save_uploaded_files
from pathlib import Path
from config import KNOWLEDGE_BASE_PATH
from utils.vectordb_utils import load_doc_retriever_by_paths

def select_category():
    st.markdown("### 📂 choose file category")
    categories = get_available_categories()
    if not categories:
        st.warning("No categories available, please create one first")
        return None
    return st.selectbox("Please select a category", categories, key="upload_category_selector")

def upload_files(category: str):
    key = f"uploader_{category}" if category else "uploader_default"
    uploaded = st.file_uploader("upload file", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True, key=key)
    if uploaded:
        file_paths = save_uploaded_files(category, uploaded)
        st.success(f"✅ {len(file_paths)} files saved")
        return file_paths
    return []

# ========================================
# 📁 file manager dialog renderer
# ========================================
def show_file_manager_dialog():
    category = select_category()

    if not category:
        return

    uploaded_paths = upload_files(category)

    st.markdown("### 📂 files in current category")
    category_path = Path("data_base/knowledge_db") / category
    files = get_files_in_category(category)
    for file in files:
        st.text(f"📄 {file.name}")
        col1, _ = st.columns([1, 4])
        delete_key = f"del_{category}_{file}"
        if col1.button("delete", key=delete_key):
            try:
                file_path = category_path / file
                if file_path.exists():
                    file_path.unlink()
                    st.success(f"✅ deleted: {file}")
                    st.rerun()
                else:
                    st.warning("⚠️ file not found")
            except Exception as e:
                st.error(f"❌ delete failed: {str(e)}")

# =============================================================
# 📁 document retrieval and classification manager
# =============================================================

def load_selected_documents_as_retriever(category: str, selected_docs: List[str]):
    """
    Load documents in a specific category to build a vector retriever.
    Parameters:
        category: category name
        selected_docs: list of selected file names (without path)
    """
    if not selected_docs:
        return None

    paths = [str(KNOWLEDGE_BASE_PATH / category / doc) for doc in selected_docs]
    return load_doc_retriever_by_paths(paths)
