import os
from pathlib import Path
from dotenv import load_dotenv
import tempfile
import json
import streamlit as st

# 检查是否在Streamlit环境中运行
def is_streamlit_env():
    try:
        return st._is_running_with_streamlit
    except:
        return False

# 从Streamlit secrets或环境变量获取值
def get_config_value(key, default=None):
    """Get configuration value from Streamlit secrets or environment variables"""
    try:
        if is_streamlit_env():
            # 先尝试从Streamlit secrets获取
            return st.secrets.get(key, os.getenv(key, default))
        else:
            # 本地环境从环境变量获取
            return os.getenv(key, default)
    except:
        # 出错时返回环境变量或默认值
        return os.getenv(key, default)

# 仅在非Streamlit环境中加载.env文件
if not is_streamlit_env():
    load_dotenv()

# 项目路径配置
BASE_DIR = Path(__file__).resolve().parent.parent

# 文件路径配置
if is_streamlit_env():
    # Streamlit Cloud环境使用临时目录以解决权限问题
    TOKEN_PATH = Path(tempfile.gettempdir()) / "token.pickle"
    CREDENTIALS_PATH = Path(tempfile.gettempdir()) / "client_secret.json"
    
    # 如果从secrets获取到Google凭据，写入临时文件以供使用
    try:
        google_creds = st.secrets.get("google_creds")
        if google_creds:
            with open(CREDENTIALS_PATH, 'w') as f:
                if isinstance(google_creds, str):
                    f.write(google_creds)
                else:
                    json.dump(google_creds, f)
    except Exception as e:
        print(f"无法写入Google凭据: {e}")
else:
    # 本地环境使用项目目录
    TOKEN_PATH = BASE_DIR / "config" / "token.pickle"
    CREDENTIALS_PATH = BASE_DIR / "client_secret.json"

# 知识库路径配置
KNOWLEDGE_BASE_PATH = BASE_DIR / "data_base/knowledge_db"
VECTOR_DB_PATH = BASE_DIR / "data_base/vector_db/chroma_db" 

# 自动创建所需目录
KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)

# Google Drive配置
DRIVE_FOLDER_ID = get_config_value('DRIVE_FOLDER_ID')
if not DRIVE_FOLDER_ID:
    print("⚠️ 警告: 未设置DRIVE_FOLDER_ID，某些功能可能不可用")

VECTOR_DRIVE_FOLDER_ID = get_config_value('VECTOR_DRIVE_FOLDER_ID')
if not VECTOR_DRIVE_FOLDER_ID:
    print("⚠️ 警告: 未设置VECTOR_DRIVE_FOLDER_ID，某些功能可能不可用")

# Google API配置
GOOGLE_API_KEY = get_config_value('GOOGLE_API_KEY')
GOOGLE_CSE_ID = get_config_value('GOOGLE_CSE_ID')

# 获取Google凭据
def get_google_creds():
    """获取Google凭据，优先从Streamlit secrets获取"""
    try:
        if is_streamlit_env():
            # 从Streamlit secrets获取
            creds = st.secrets.get("google_creds")
            if creds:
                return json.loads(creds) if isinstance(creds, str) else creds
        
        # 如果不在Streamlit环境或未从secrets获取到，尝试从文件读取
        if CREDENTIALS_PATH.exists():
            with open(CREDENTIALS_PATH, 'r') as f:
                return json.load(f)
        
        return None
    except Exception as e:
        print(f"加载Google凭据时出错: {e}")
        return None

# 应用配置
APP_TITLE = "📚Your Personal Knowledge Base"
APP_ICON = "📚"
LAYOUT = get_config_value("LAYOUT", "wide")
INITIAL_SIDEBAR_STATE = get_config_value("INITIAL_SIDEBAR_STATE", "expanded")

# 模型配置
AVAILABLE_MODELS = ["mistral:7b-instruct", "deepseek-coder:6.7b"]
DEFAULT_MODEL = get_config_value("DEFAULT_MODEL", "mistral:7b-instruct")
TEMPERATURE = float(get_config_value("TEMPERATURE", "0.7"))

# Embedding模型配置
EMBEDDING_MODEL = get_config_value("EMBEDDING_MODEL", "bge-m3:latest")

# API配置和数据库
OLLAMA_URL = get_config_value("OLLAMA_URL", "http://localhost:11434")
DATABASE_URL = get_config_value("DATABASE_URL", "sqlite:///./google_drive_sync.db")

# 文档处理配置
CHUNK_SIZE = int(get_config_value("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(get_config_value("CHUNK_OVERLAP", "200"))
TEXT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

# Web搜索配置
if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    print("⚠️ 警告: GOOGLE_API_KEY或GOOGLE_CSE_ID未设置，网络搜索功能不可用")

USE_WEB_SEARCH = get_config_value("USE_WEB_SEARCH", "False").lower() == "true"

# 调试信息
if is_streamlit_env():
    print("🚀 在Streamlit环境中运行，使用Streamlit secrets配置")
else:
    print("🖥️ 在本地环境中运行，使用.env配置")

# 导出所有配置变量
__all__ = [
    "KNOWLEDGE_BASE_PATH",
    "VECTOR_DB_PATH",
    "DRIVE_FOLDER_ID",
    "VECTOR_DRIVE_FOLDER_ID",
    "CREDENTIALS_PATH",
    "TOKEN_PATH",
    "get_google_creds",
    "EMBEDDING_MODEL",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "OLLAMA_URL",
    "USE_WEB_SEARCH",
    "APP_TITLE",
    "APP_ICON",
    "LAYOUT",
    "AVAILABLE_MODELS",
    "DEFAULT_MODEL",
    "TEMPERATURE",
]