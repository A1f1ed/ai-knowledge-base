from typing import List, Optional
from pathlib import Path
from langchain.vectorstores import Chroma
from langchain.schema import BaseRetriever
from config import KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH
from utils.model_utils import get_embedding_model
from utils.file_utils import save_uploaded_file
from utils.vectordb_utils import embed_single_file, CHROMA_SETTINGS

def get_category_docs_retriever(category: str, selected_files: List[str]) -> Optional[BaseRetriever]:
    """
    Load selected documents under a given category as a retriever.
    Only documents in `selected_files` will be loaded into the retriever.
    """
    if not selected_files:
        return None

    embedding_model = get_embedding_model()
    if not embedding_model:
        return None

    # specify the vector store path: like data_base/vector_db/chroma_db/{category}
    category_db_path = VECTOR_DB_PATH / category

    # load Chroma vector store (persistent)
    vectordb = Chroma(
        collection_name=category,
        persist_directory=str(category_db_path),
        embedding_function=embedding_model,
        client_settings=CHROMA_SETTINGS
    )

    # filter specified files based on metadata['source'] (full path matching)
    selected_paths = [str(KNOWLEDGE_BASE_PATH / category / f) for f in selected_files]

    # create retriever using the new API
    retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs={
            "filter": {"source": {"$in": selected_paths}},
            "k": 5
        }
    )
    return retriever

def process_uploaded_file(uploaded_file, category: str) -> bool:
    file_path = save_uploaded_file(uploaded_file, category)
    return embed_single_file(Path(file_path), category)

__all__ = [
    "get_category_docs_retriever",
    "process_uploaded_file"
]