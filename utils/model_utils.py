import requests
import logging
from config.config import OLLAMA_URL, TEMPERATURE, AVAILABLE_MODELS, EMBEDDING_MODEL
from langchain_ollama import ChatOllama
import streamlit as st

logger = logging.getLogger(__name__)
import requests
import numpy as np
from config.config import OLLAMA_URL, EMBEDDING_MODEL

class LocalOllamaEmbeddingModel:
    def __init__(self, model_name=EMBEDDING_MODEL, base_url=OLLAMA_URL):
        self.model = model_name
        self.base_url = base_url

    def embed_query(self, text: str) -> list[float]:
        return self._get_embedding(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._get_embedding(text) for text in texts]

    def _get_embedding(self, text: str) -> list[float]:
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text}
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
# ===================================
# LLM loader
# ===================================
def get_llm(selected_model: str, api_key: str = None):
    """
    Return the corresponding LangChain LLM instance based on the model name.
    Currently only supports local Ollama models.
    """
    if selected_model not in AVAILABLE_MODELS:
        st.error(f"❌ model '{selected_model}' is not in the allowed model list")
        return None

    try:
        return ChatOllama(
            model=selected_model,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL
        )
    except Exception as e:
        st.error(f"❌ failed to load model: {e}")
        logger.error(f"failed to load LLM model: {e}", exc_info=True)
        return None

# ===================================
# embedding model loader
# ===================================
def get_embedding_model():
    """
    Return the embedding model instance.
    Currently fixed to use Ollama model to call bge-m3 or other models available on OLLAMA_URL.
    """
    try:
        print(f"[DEBUG] the current embedding model is: {EMBEDDING_MODEL}")
        from utils.model_utils import LocalOllamaEmbeddingModel
        return LocalOllamaEmbeddingModel()
    except Exception as e:
        st.error(f"❌ failed to load embedding model: {e}")
        logger.error(f"failed to load embedding model: {e}", exc_info=True)
        
        return None

# ===================================
# Ollama service check
# ===================================
def check_ollama_status():
    """
    Check if the local Ollama model service is running.
    """
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags")
        return res.status_code == 200
    except Exception:
        return False

# ===================================
# get the available model list (can be used for dropdown)
# ===================================
def get_available_ollama_models():
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags")
        if res.status_code == 200:
            data = res.json()
            return [m['name'] for m in data.get("models", [])]
        return []
    except Exception:
        return []

def get_llm_response(llm, prompt: str):
    """
    Call LLM to return the answer and reference documents (if any).

    Args:
        llm: initialized language model object
        prompt: the prompt string after user question concatenation

    Returns:
        tuple(str, list): the answer text and optional source documents list
    """
    try:
        response = llm.invoke(prompt)
        if response is None:
            return "⚠️ the model did not return any results", []

        # check if the response is a LangChain document type
        if hasattr(response, "content"):
            return response.content, getattr(response, "source_documents", [])

        return str(response), []

    except Exception as e:
        return f"❌ failed to call LLM: {str(e)}", []