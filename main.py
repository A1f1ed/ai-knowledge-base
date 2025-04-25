import streamlit as st
from components.ui import (
    render_sidebar_controls,
    render_upload_section,
    render_chat_mode_selector,
    render_document_selection_if_needed,
    render_chat_box,
)

def main():
    st.set_page_config(layout="wide")

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