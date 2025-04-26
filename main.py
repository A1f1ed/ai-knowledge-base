import streamlit as st
import logging
import sys
import traceback
import os
from pathlib import Path
import tempfile
from components.ui import (
    render_sidebar_controls,
    render_upload_section,
    render_chat_mode_selector,
    render_document_selection_if_needed,
    render_chat_box,
)

# 确保临时目录存在和可写
TEMP_DIR = tempfile.gettempdir()
os.makedirs(os.path.join(TEMP_DIR, "chroma_fallback"), exist_ok=True)
os.makedirs(os.path.join(TEMP_DIR, "vectordb"), exist_ok=True)

# 设置页面配置（必须是第一个 Streamlit 命令）
st.set_page_config(
    page_title="Knowledge Base",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 检查系统环境
def check_environment():
    """检查和记录系统环境信息"""
    try:
        import platform
        logger.info(f"操作系统: {platform.system()} {platform.release()}")
        logger.info(f"Python版本: {platform.python_version()}")
        logger.info(f"临时目录位置: {TEMP_DIR}")
        
        # 检查关键库版本
        import chromadb
        logger.info(f"ChromaDB版本: {chromadb.__version__}")
        
        import langchain
        logger.info(f"LangChain版本: {langchain.__version__}")
        
        # 检查目录权限
        from config.config import KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH
        logger.info(f"知识库路径: {KNOWLEDGE_BASE_PATH}")
        logger.info(f"向量数据库路径: {VECTOR_DB_PATH}")
        
        # 确保关键目录存在
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        logger.error(f"环境检查错误: {str(e)}")
        return False

# 错误处理装饰器
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"An error occurred: {str(e)}")
            with st.expander("详细错误信息"):
                st.code(traceback.format_exc())
            if st.button("重试"):
                st.experimental_rerun()
    return wrapper

@handle_errors
def main():
    """主应用入口点"""
    try:
        # 检查环境
        check_environment()
        
        # 初始化向量数据库结构
        from utils.vectordb_utils import ensure_vector_db_structure
        ensure_vector_db_structure()
        
        # Combine all sidebar components
        with st.sidebar:
            # st.title("🧠 AI Assistant Settings")
            selected_model, web_search_enabled = render_sidebar_controls()
            
            st.divider()
            st.title("📁 Knowledge Base")
            render_upload_section()

        # Main content area
        # mode selection and document selection
        chat_mode = render_chat_mode_selector()
        selected_category, selected_docs = render_document_selection_if_needed(chat_mode)

        # chat area
        render_chat_box(
            selected_model=selected_model,
            chat_mode=chat_mode,
            web_search_enabled=web_search_enabled,
            selected_category=selected_category,
            selected_docs=selected_docs,
        )
    except Exception as e:
        logger.error(f"应用启动错误: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"应用启动失败: {str(e)}")
        st.info("请尝试刷新页面或联系管理员")
        with st.expander("技术详情"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()