from langchain.chains import ConversationalRetrievalChain
import streamlit as st
from utils.api_handler import APIHandler

def perform_web_search(query: str) -> list:
    try:
        api_handler = APIHandler()
        results = api_handler.search_web(query)
        return results.get("google", {}).get("data", [])
    except Exception as e:
        print(f"❌ web search failed: {str(e)}")
        return []

def format_chat_history(chat_history: list) -> str:
    """
    Format the recent user and AI conversation into a string for Prompt concatenation.
    """
    if not chat_history:
        return ""

    lines = []
    for msg in chat_history[-5:]:  # Default to last 5 conversations
        prefix = "User: " if msg.get("role") == "user" else "AI: "
        content = msg.get("content", "")
        lines.append(f"{prefix}{content}")
    
    return "\n".join(lines)

def format_search_results(search_results: list) -> str:
    """
    Format web search results into a string for LLM usage.
    """
    if not search_results:
        return "⚠️ No relevant search results found"

    formatted = []
    for item in search_results:
        title = item.get("title", "Unknown title")
        snippet = item.get("snippet", "No summary available")
        link = item.get("link", "#")
        formatted.append(f"📌 **{title}**\n📝 **Summary**：{snippet}\n🔗 **Source**：{link}")
    
    return "\n\n".join(formatted)

def get_chat_qa_chain(llm, retriever_or_vectorstore):
    """
    Create Conversational QA chain, return LangChain's RAG pipeline.

    Args:
        llm: Initialized language model
        retriever_or_vectorstore: Can be a retriever object or a vector database object

    Returns:
        ConversationalRetrievalChain instance
    """
    if not llm or not retriever_or_vectorstore:
        st.error("Please ensure LLM and retriever are initialized")
        return None

    try:
        # If the input is a vector store, get its retriever
        if hasattr(retriever_or_vectorstore, 'as_retriever'):
            retriever = retriever_or_vectorstore.as_retriever()
        else:
            # If the input is already a retriever, use it directly
            retriever = retriever_or_vectorstore
            
        return ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            verbose=False,
            memory=None  # Disable built-in memory, we use our own chat history management
        )
    except Exception as e:
        st.error(f"Failed to create QA chain: {str(e)}")
        return None




def perform_web_search(query: str) -> list:
    """
    Call APIHandler to perform web search.
    """
    try:
        api_handler = APIHandler()
        results = api_handler.search_web(query)
        return results.get("data", [])  # Extract from results['data']
    except Exception as e:
        print(f"❌ web search failed: {str(e)}")
        return []

__all__ = ["format_chat_history", "format_search_results", "perform_web_search"]

__all__ = ["search_web"]