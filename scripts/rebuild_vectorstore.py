import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import shutil
from utils.vectordb_utils import rebuild_vectordb_for_files
from utils.file_utils import get_knowledge_base_files
from config.config import VECTOR_DB_PATH

def rebuild_vectorstore():
    """rebuild vector store"""
    try:
        # 1. get all knowledge base files
        files = get_knowledge_base_files()
        if not files:
            print("no documents found")
            return
        
        # 2. delete existing vector store
        vector_db_path = Path(VECTOR_DB_PATH)
        if vector_db_path.exists():
            print(f"delete existing vector store: {vector_db_path}")
            shutil.rmtree(vector_db_path)
        
        # 3. rebuild vector store
        print(f"start rebuilding vector store, processing {len(files)} files...")
        # convert file paths to (category, filename) tuples
        file_tuples = []
        for file_path in files:
            path = Path(file_path)
            category = path.parent.name
            filename = path.name
            file_tuples.append((category, filename))
            
        vectordb = rebuild_vectordb_for_files(file_tuples)
        
        if vectordb:
            print("vector store rebuilt successfully!")
        else:
            print("vector store rebuild failed!")
            
    except Exception as e:
        print(f"error rebuilding vector store: {str(e)}")

if __name__ == "__main__":
    print("start rebuilding vector store...")
    rebuild_vectorstore()


