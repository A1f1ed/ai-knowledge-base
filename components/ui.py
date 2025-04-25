import streamlit as st
from pathlib import Path
from utils.manager_utils import get_available_categories, get_files_in_category, delete_file
from core.document_chat_controller import process_uploaded_file
from services.google_drive_service import sync_from_drive
from config.config import KNOWLEDGE_BASE_PATH
from streamlit import secrets

# ============================
# file upload and management area
# ============================
def select_category():
    st.markdown("### 📂 choose file category")
    categories = get_available_categories()
    if not categories:
        st.warning("No categories available, please create one first")
        return None
    return st.selectbox("Please select a category", categories, key="upload_category_selector")


def show_file_manager_dialog(category: str):
    """Show the file manager dialog for the selected category"""
    if not category:
        return

    files = get_files_in_category(category)
    if not files:
        st.info(f"No files in category: {category}")
        return

    # Display files with select all checkbox
    select_all = st.checkbox("Select all", key="select_all")
    
    selected_files = []
    for file in files:
        is_selected = st.checkbox(
            file,
            value=select_all,
            key=f"file_{file}"
        )
        if is_selected:
            selected_files.append(file)

    # Delete button for selected files
    if selected_files:
        if st.button("🗑️ Delete Selected", use_container_width=True):
            with st.spinner("Deleting files..."):
                for file in selected_files:
                    delete_file(category, file)
                st.rerun()

    # Store selected files in session state
    st.session_state["selected_files"] = selected_files


def render_upload_section():
    """Render the file upload section in the sidebar"""
    # Category selection
    selected_category = select_category()
    
    # Upload files section
    st.write("📤 Upload Files")
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed"
    )

    if uploaded_files:
        process_uploaded_files(uploaded_files, selected_category)

    # Show files in current category
    st.write("📑 Files in Category")
    show_file_manager_dialog(selected_category)

    DRIVE_FOLDER_ID = secrets.get("DRIVE_FOLDER_ID", None)

    # Google Drive sync button
    st.divider()

    if DRIVE_FOLDER_ID is not None:
        if st.button("🔄 Sync with Google Drive", use_container_width=True):
            with st.spinner("Syncing with Google Drive..."):
                if sync_from_drive():
                    st.success("Successfully synced with Google Drive!")
                else:
                    st.error("Failed to sync with Google Drive.")
    else:
        st.warning("🔒 Google Drive Sync is disabled in cloud mode.")


# ============================
# model settings area (left)
# ============================
def render_sidebar_controls():
    st.sidebar.title("🧠 AI Assistant Settings")
    selected_model = st.sidebar.selectbox(
        "Choose a model:",
        ["mistral:7b-instruct", "deepseek-coder"],
        key="model_selector",
    )
    use_web = st.sidebar.checkbox("🌐 Use Web Search", key="use_web_checkbox")
    
    return selected_model, use_web


# ============================
# category document selection area (middle)
# ============================
def render_document_selection_if_needed(chat_mode: str):
    if chat_mode != "category_qa":
        return None, []

    selected_category = st.selectbox(
        "Select a category:", get_available_categories(), key="doc_category_selector"
    )

    selected_docs = []
    if selected_category:
        category_files = get_files_in_category(selected_category)
        selected_docs = st.multiselect(
            "Choose document(s) for Q&A:", category_files, key="doc_selector"
        )

    return selected_category, selected_docs


# ============================
# chat mode selection area
# ============================
def render_chat_mode_selector():
    st.markdown("### 🤖 Select Chat Mode")
    chat_mode = st.radio(
        "Choose one:",
        ["free_chat", "category_qa", "knowledge_chat"],
        format_func=lambda x: {
            "free_chat": "💬 Web + Local (Fallback)",
            "category_qa": "📁 Category Documents",
            "knowledge_chat": "🌐 All Knowledge Base",
        }[x],
        key="chat_mode_selector",
        horizontal=True,
    )
    return chat_mode


# ============================
# chat box area
# ============================
def render_chat_box(
    selected_model,
    chat_mode,
    web_search_enabled,
    selected_category=None,
    selected_docs=None,
):
    st.markdown("### 💬 Ask a Question")
    
    # Add refresh button
    if st.button("🔄 Refresh Chat", key="refresh_chat"):
        st.session_state.chat_history = []
        st.rerun()
    
    # initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # show chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # user input
    user_input = st.chat_input("Your question")

    if user_input:
        # show user message
        with st.chat_message("user"):
            st.write(user_input)
        
        from core.chat_controller import handle_chat

        with st.spinner("thinking..."):
            answer, sources = handle_chat(
                user_question=user_input,
                chat_mode=chat_mode,
                selected_model=selected_model,
                chat_history=st.session_state.chat_history,
                web_search_enabled=web_search_enabled,
                selected_category=selected_category,
                selected_docs=selected_docs,
            )

        # show AI answer
        with st.chat_message("assistant"):
            st.write(answer)

        # update chat history
        st.session_state.chat_history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": answer}
        ])

        if sources:
            with st.expander("📎 Sources"):
                for s in sources:
                    st.markdown(f"- {s.page_content[:100]}...")

def render_sidebar():
    with st.sidebar:
        st.title("knowledge base management")
        
        # file upload section
        render_upload_section()
        
        # Google Drive sync button
        st.divider()
        st.subheader("Google Drive sync")
        if st.button("sync from Google Drive", type="primary"):
            with st.spinner("syncing files..."):
                if sync_from_drive():
                    st.success("sync completed!")
                    st.rerun()  # refresh page to show new files
                else:
                    st.error("sync failed, please check the logs")

def process_uploaded_files(uploaded_files, selected_category):
    """Process uploaded files and save them to the selected category"""
    if not selected_category:
        st.error("Please select a category first")
        return
        
    with st.spinner("Processing uploaded files..."):
        for uploaded_file in uploaded_files:
            process_uploaded_file(uploaded_file, selected_category)
        st.success("Files uploaded successfully!")
        st.rerun()  # refresh to show new files