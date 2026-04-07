# Rubberduck

**Rubberduck** is a small helper tool I use to manage my research and consolidate a few workflows that I found myself repeatedly using other tools for, but none were as flexible as just making my own. It is a desktop AI chat application and personal assistant that runs directly on your machine, providing a fast, privacy-focused environment with built-in support for Retrieval-Augmented Generation (RAG) over your own projects and notes.

### Features
- **Flexible LLM Support**: Connect to Ollama (local), Google Gemini/Vertex AI, or OpenAI.
- **Context-Aware Projects**: Organize your chats, documents, and notes into distinct workspaces.
- **Built-in RAG**: Chat directly with your uploaded resources using automated vector search and context retrieval.
- **Integrated Workspace**: A customizable UI with a sidebar for projects, a central chat area, and a dedicated markdown notes panel.

### Installation

Ensure you have Node.js, Python 3.9+, and Rust installed on your system.

1. **Install frontend dependencies**
   ```bash
   npm install
   ```

2. **Set up the Python sidecar**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r src-python/requirements.txt
   ```

3. **Run the application locally**
   ```bash
   npm run dev
   ```

### Usage

- **Start a Project**: Launch the app and create a new project from the left sidebar to isolate your context.
- **Add Knowledge**: Type notes into the right-hand Notes panel or upload documents. The app automatically indexes these for RAG.
- **Chat**: Ask questions in the central chat area. Rubberduck will pull relevant context from your project notes to inform its answers.
- **Configure Models**: Open the Settings dialog to swap between Ollama (defaulting to `http://localhost:11434`), Vertex AI, or OpenAI based on your API keys and local setup.

> *Docs generated with [documentor](https://github.com/YusufHosny/documentor)*