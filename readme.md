# Knowledge Base Assistant

A powerful knowledge base management system with AI-powered question answering capabilities.

## Why This Project?

Managing large personal or team knowledge collections can be overwhelming.  
This assistant helps you query, organize, and update your documents with AI support – all locally and securely.

## Features

- 📚 Knowledge Base Management
  - Organize documents by categories
  - Upload multiple file formats
  - Google Drive integration for file sync
  - Easy file management (upload, delete, browse)

- 🤖 AI-Powered Chat Modes
  - Free Chat: Web + Local knowledge fallback
  - Category Q&A: Query specific document sets
  - Knowledge Base: Search across all documents
  
- 🔍 Advanced Features
  - Web search integration
  - Multiple AI model support
  - Source citation for answers
  - Real-time chat interface

## Quick Start


### Manual Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd knowledge-base-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run main.py
```

## Configuration

1. Google Drive Integration (Optional):
- Place your `client_secret.json` in the project root
- First sync will require authentication

2. AI Model Selection:
- Default: Mistral 7B (requires Ollama)
- Can be configured in settings

## Project Structure

```
knowledge-base-assistant/
├── components/        # UI components
├── core/             # Core business logic
├── services/         # External services integration
├── utils/            # Utility functions
└── data_base/        # Knowledge base storage
```

## Requirements

- Python 3.10+
- Streamlit
- LangChain
- (Optional) Ollama for local AI models

## Notes

- Files are stored in categorized folders
- Supports multiple document formats
- Web search is optional and can be enabled/disabled
- All chat history is session-based and not persisted

## License

MIT License

