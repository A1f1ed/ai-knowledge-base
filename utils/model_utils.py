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
        st.error(f"❌ 模型 '{selected_model}' 不在允许的模型列表中")
        return None

    try:
        # 首先检查Ollama服务是否可用
        if not check_ollama_status():
            error_msg = "❌ Ollama服务不可用。请确保您已安装并启动Ollama服务（https://ollama.ai/）"
            st.error(error_msg)
            logger.error(error_msg)
            return None
            
        # 检查所需的LLM模型是否可用
        models = get_available_ollama_models()
        if selected_model not in models:
            error_msg = f"❌ 模型 '{selected_model}' 在Ollama服务中不可用。请运行 'ollama pull {selected_model}' 下载模型"
            st.error(error_msg)
            logger.error(error_msg)
            return None
            
        return ChatOllama(
            model=selected_model,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL
        )
    except Exception as e:
        error_msg = f"❌ 无法加载模型: {e}"
        st.error(error_msg)
        logger.error(error_msg, exc_info=True)
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
        
        # 首先检查Ollama服务是否可用
        if not check_ollama_status():
            error_msg = "❌ Ollama服务不可用。请确保您已安装并启动Ollama服务（https://ollama.ai/）"
            st.error(error_msg)
            logger.error(error_msg)
            return None
            
        # 检查所需的嵌入模型是否可用
        models = get_available_ollama_models()
        if EMBEDDING_MODEL not in models and not EMBEDDING_MODEL.startswith("bge-"):
            error_msg = f"❌ 嵌入模型 '{EMBEDDING_MODEL}' 在Ollama服务中不可用。请运行 'ollama pull {EMBEDDING_MODEL}' 下载模型"
            st.error(error_msg)
            logger.error(error_msg)
            return None
            
        from utils.model_utils import LocalOllamaEmbeddingModel
        return LocalOllamaEmbeddingModel()
    except Exception as e:
        error_msg = f"❌ 无法加载嵌入模型: {e}"
        st.error(error_msg)
        logger.error(error_msg, exc_info=True)
        return None

# ===================================
# Ollama service check
# ===================================
def check_ollama_status():
    """
    Check if the local Ollama model service is running.
    """
    try:
        print(f"[DEBUG] 尝试连接Ollama服务: {OLLAMA_URL}")
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if res.status_code == 200:
            print(f"[DEBUG] Ollama服务连接成功: {res.status_code}")
            print(f"[DEBUG] 可用模型: {[m['name'] for m in res.json().get('models', [])]}")
            return True
        else:
            print(f"[DEBUG] Ollama服务返回错误状态码: {res.status_code}")
            return False
    except Exception as e:
        print(f"[DEBUG] 连接Ollama服务失败: {str(e)}")
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