import streamlit as st
from utils.model_utils import get_llm_response, get_llm
from utils.chat_utils import format_chat_history, perform_web_search
from core.prompt_templates import (
    get_free_chat_prompt,
    get_document_chat_prompt,
    get_knowledge_chat_prompt
)
from utils.chat_utils import get_chat_qa_chain
from utils.vectordb_utils import get_vectordb
from core.document_chat_controller import get_category_docs_retriever
from config import USE_WEB_SEARCH, KNOWLEDGE_BASE_PATH
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def handle_chat(user_question: str,
                chat_mode: str = "free_chat",
                selected_model: str = None,
                chat_history=None,
                web_search_enabled: bool = False,
                selected_category: str = None,
                selected_docs: list = None):
    """
    multi-mode unified entry, different QA processes according to different modes.
    Returns:
        answer: str
        source_documents: List[Document]
    """
    answer, source_documents = "⚠️ no response", []

    try:
        # Initialize LLM
        llm = get_llm(selected_model)
        
        if chat_mode == "free_chat":
            history = format_chat_history(chat_history or [])
            prompt = get_free_chat_prompt(history, user_question)

            if web_search_enabled:
                try:
                    web_results = perform_web_search(user_question)
                    if web_results:
                        enhanced_prompt = get_free_chat_prompt(
                            history, user_question, draft=answer, web_results=web_results
                        )
                        answer, source_documents = get_llm_response(
                            llm, enhanced_prompt, web_results
                        )
                    else:
                        raise ValueError("search failed or no search results")
                except Exception as e:
                    print(f"❌ web search failed: {e}")
                    answer, source_documents = get_llm_response(llm, prompt)
            else:
                print("🌐 USE_WEB_SEARCH=False, web search skipped")
                answer, source_documents = get_llm_response(llm, prompt)

        elif chat_mode == "category_qa":
            # 1. first check if the category and docs are selected
            if not selected_category or not selected_docs:
                st.warning("⚠️ please select category and docs first")
                return "⚠️ please select category and docs first", []

            st.info(f"📂 using the following files in category '{selected_category}' for question answering:\n" + "\n".join([f"- {doc}" for doc in selected_docs]))

            # 2. 获取检索器
            retriever = get_category_docs_retriever(
                category=selected_category,
                selected_files=selected_docs
            )
            if not retriever:
                st.error("⚠️ cannot load document retriever, please ensure the docs are correctly vectorized")
                return "⚠️ document loading failed", []

            try:
                # 3. create QA Chain
                qa_chain = get_chat_qa_chain(llm, retriever)
                if not qa_chain:
                    return "⚠️ QA Chain initialization failed", []
                
                # 4. execute question answering
                response = qa_chain.invoke({
                    "question": user_question,
                    "chat_history": chat_history or []
                })
                answer = response.get("answer", "unable to get answer")
                source_documents = response.get("source_documents", [])
                
                # display source file names
                if source_documents:
                    source_files = set()
                    for doc in source_documents:
                        source_path = Path(doc.metadata.get("source", ""))
                        if source_path.exists():
                            source_files.add(source_path.name)
                    if source_files:
                        st.info("📚 the answer is from the following files:\n" + "\n".join([f"- {f}" for f in sorted(source_files)]))
                
                return answer, source_documents
                
            except Exception as e:
                st.error(f"error processing question: {str(e)}")
                return f"⚠️ processing failed: {str(e)}", []

        elif chat_mode == "knowledge_chat":
            # 1. get the global vector store
            vectorstore = get_vectordb()
            if not vectorstore:
                # try to initialize the global vector store
                from utils.vectordb_utils import ensure_global_vectordb
                if not ensure_global_vectordb():
                    st.error("⚠️ cannot initialize the global vector store, please ensure the docs are uploaded")
                    return "⚠️ global vector store initialization failed, please upload some docs first", []
                vectorstore = get_vectordb()
                if not vectorstore:
                    st.error("⚠️ cannot load the global vector store")
                    return "⚠️ global vector store loading failed", []

            try:
                # 2. create QA Chain
                qa_chain = get_chat_qa_chain(llm, vectorstore)
                if not qa_chain:
                    return "⚠️ QA Chain initialization failed", []
                
                # 3. execute question answering
                response = qa_chain.invoke({
                    "question": user_question,
                    "chat_history": chat_history or []
                })
                answer = response.get("answer", "unable to get answer")
                source_documents = response.get("source_documents", [])
                
                # 4. display source file names
                if source_documents:
                    source_files = set()
                    for doc in source_documents:
                        source_path = Path(doc.metadata.get("source", ""))
                        if source_path.exists():
                            # get the relative path, display the category/filename format
                            rel_path = source_path.relative_to(KNOWLEDGE_BASE_PATH)
                            source_files.add(f"{rel_path.parent.name}/{rel_path.name}")
                    if source_files:
                        st.info("📚 the answer is from the following files:\n" + "\n".join([f"- {f}" for f in sorted(source_files)]))
                
                return answer, source_documents
                
            except Exception as e:
                logger.error(f"[QA] Error in knowledge_chat mode: {e}")
                st.error(f"error processing question: {str(e)}")
                return f"⚠️ processing failed: {str(e)}", []

        return answer, source_documents

    except Exception as e:
        logging.error(f"Chat handling error: {str(e)}")
        return f"Sorry, an error occurred: {str(e)}", None

__all__ = ["handle_chat"]

from utils.file_utils import save_uploaded_file
from utils.vectordb_utils import embed_single_file

def process_uploaded_file(uploaded_file, category: str) -> bool:
    file_path = save_uploaded_file(uploaded_file, category)
    return embed_single_file(file_path, category)