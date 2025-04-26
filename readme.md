## License

⚠️ This repository is for classroom demo only. Please do not reuse or fork this repo.

# Personal Knowledge Base

A local-first personal knowledge base application that integrates document management, vector embedding, and AI-powered Q&A capabilities.

## Features

- **Document Management**: Upload, categorize, and organize documents in a multi-level folder structure
- **Google Drive Sync**: Automatically sync documents with Google Drive for backup and accessibility
- **Vector Search**: Convert documents into semantic vectors for efficient retrieval
- **AI Question Answering**: Ask questions about your documents in natural language
- **Privacy-First**: Run locally with your own models, keeping your data private

## Getting Started

### Prerequisites

- Python 3.10+
- Docker (optional, for running Ollama)
- Google account (for Drive integration)

### Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/personal-knowledge-base.git
cd personal-knowledge-base
```

2. Create a virtual environment
```bash
python -m venv venv_kbs
source venv_kbs/bin/activate  # On Windows: venv_kbs\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up Google Drive API
   - Create a project in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Google Drive API
   - Create OAuth 2.0 credentials
   - Download the credentials as `client_secret.json` and place in the project root

5. Configure environment variables by copying the example
```bash
cp .env.example .env
```

6. Set up Ollama (for local LLM)
   - Install [Ollama](https://ollama.ai/) or use the Docker configuration
   - Pull required models:
```bash
ollama pull mistral:7b-instruct
ollama pull bge-m3:latest
```

### Running the Application

**Option 1: Local Development**
```bash
streamlit run main.py
```

**Option 2: Using Docker**
```bash
docker-compose up -d
```

## Configuration

Edit the `.env` file to customize your setup:

- `OLLAMA_URL`: URL for your Ollama instance (default: http://localhost:11434)
- `DRIVE_FOLDER_ID`: Google Drive folder ID for document storage
- `VECTOR_DRIVE_FOLDER_ID`: Google Drive folder ID for vector database backup
- `USE_WEB_SEARCH`: Enable/disable web search for question answering

## Architecture

- **Frontend**: Streamlit-based UI for interaction
- **Document Processing**: Converts documents to vectors using embedding models
- **Vector Database**: ChromaDB for efficient semantic search
- **LLM Integration**: Local Ollama models (default: Mistral 7B)
- **Storage**: Local files with Google Drive synchronization

## Deploying to Streamlit Cloud

1. Push your code to GitHub
2. Connect your repository in Streamlit Cloud
3. Configure the following secrets in Streamlit Cloud:
   - `google_creds`: Content of your Google credentials JSON file
   - Add any additional environment variables from your `.env` file

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

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



