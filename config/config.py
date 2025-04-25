import os
from pathlib import Path
from dotenv import load_dotenv

# load environment variables
load_dotenv()


# project path configuration
BASE_DIR = Path(__file__).resolve().parent.parent

# path configuration
CREDENTIALS_PATH = BASE_DIR / "client_secret.json"
TOKEN_PATH = BASE_DIR / "token.pickle"
KNOWLEDGE_BASE_PATH = BASE_DIR / "data_base" / "knowledge_db"
VECTOR_DB_PATH = BASE_DIR / "data_base" / "vector_db" / "chroma_db"

# automatically create required directories
KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)

# application configuration
APP_TITLE = "📚Your Personal Knowledge Base"
APP_ICON = "📚"
LAYOUT = "wide"  
INITIAL_SIDEBAR_STATE = "expanded"

# model configuration
AVAILABLE_MODELS = ["mistral:7b-instruct", "deepseek-coder:6.7b"]
DEFAULT_MODEL = "mistral:7b-instruct"
TEMPERATURE = 0.7

# Embedding model configuration
EMBEDDING_MODEL = "bge-m3:latest"  

# API configuration and database
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")  
DATABASE_URL = "sqlite:///./google_drive_sync.db"


# document processing configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TEXT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]



# Google Drive folder ID - only get from environment variable
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')
if not DRIVE_FOLDER_ID:
    raise ValueError("Please set DRIVE_FOLDER_ID in environment variables") 


# ================================
# 🌐 Google Web Search configuration
# ================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    print("⚠️ warning: GOOGLE_API_KEY or GOOGLE_CSE_ID not detected, please check .env configuration")

USE_WEB_SEARCH = os.getenv("USE_WEB_SEARCH", "False").lower() == "true"