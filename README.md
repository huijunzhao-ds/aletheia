
# Aletheia | Multimedia Research Assistant

A modern research interface separated into a React frontend and a Python backend (ADK-compatible).

## Prerequisites

- **Python 3.9+**
- **Node.js** (for frontend development)
- **Google Gemini API Key** (for real agent logic)

## 1. Backend Setup (Python)

The backend is built with FastAPI and is designed to act as a bridge for your AI agent.

```bash
# Install dependencies
pip install fastapi uvicorn pydantic

# (Optional) If using the Google GenAI SDK
# pip install -U google-genai

# Run the server
python main.py
```
The backend will start at `http://localhost:8000`. It includes:
- CORS support for the frontend.
- A static file server at `/files` for your generated MP3, MP4, and PPTX assets.

## 2. Frontend Setup

The frontend is a React application utilizing Tailwind CSS and esm.sh for dependencies.

1. Open `index.html` in your browser (if using a local live server).
2. The UI will automatically try to connect to the backend at `localhost:8000/api/research`.

## 3. Integration Details

- **Port**: The frontend expects the backend on port `8000`.
- **Payload**:
  - `POST /api/research`
  - Body: `{ "query": "string", "mode": "Quick Search" | "Deep Research" }`
- **Response**:
  - `{ "content": "markdown_string", "files": [{ "path": "url", "type": "mp3|mp4|pptx", "name": "string" }] }`

## 4. Media Storage

Place any generated files in the `output_files/` folder on your backend. They will be served at `http://localhost:8000/files/yourfile.ext`.
