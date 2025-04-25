

from utils.manager_utils import get_available_categories
from utils.file_utils import get_knowledge_base_files
from utils.vectordb_utils import add_documents_to_vectordb


def update_all_categories_to_vectordb():
      
    try:
        
        categories = get_available_categories()
        all_files = []

        for category in categories:
            file_paths = get_knowledge_base_files(category)
            all_files.extend(file_paths)

        if all_files:
            return add_documents_to_vectordb(all_files)
        return None
    except Exception as e:
        print(f"update vector store failed: {e}")
        return None
    
__all__ = ["update_all_categories_to_vectordb"]
