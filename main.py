import streamlit as st
import logging
import sys
from pathlib import Path
from components.ui import (
    render_sidebar_controls,
    render_upload_section,
    render_chat_mode_selector,
    render_document_selection_if_needed,
    render_chat_box,
)

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

# 错误处理装饰器
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
            if st.button("Retry"):
                st.experimental_rerun()
    return wrapper

def main():
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

if __name__ == "__main__":
    main()