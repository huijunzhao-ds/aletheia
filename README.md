
# Aletheia | Multimedia Research Assistant

A modern research interface separated into a React frontend and a Python backend (ADK-compatible).

## Prerequisites

- **Python 3.10+** (managed via uv)
- **Node.js** (for frontend development)
- **Google Gemini API Key** (set in `.env` as `GOOGLE_API_KEY`)
- **uv**: [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

## 1. Environment Setup

Create a `.env` file in the **root directory** of the project (`aletheia/.env`) with the following content:

```env
GOOGLE_API_KEY="your-google-gemini-api-key"
```

## 2. Backend Setup (Python)

The backend is built with FastAPI and Google's Agent Development Kit (ADK). It is managed using `uv`.

```bash
# 1. Create virtual environment
uv venv .venv

# 2. Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload --port 8000
```
The backend will start at `http://localhost:8000`. It includes:
- **Agent Endpoint**: `POST /api/research` handling the ReAct agent logic.
- **Static Files**: Serves generated audio/video/slides from `/static` at `http://localhost:8000/static`.

## 3. Frontend Setup

The frontend is a React application built with Vite.

```bash
# 1. Install dependencies
npm install

# 2. Run the development server
npm run dev
```

Open the URL shown in the terminal (usually `http://localhost:5173`) to interact with Aletheia.

## 4. Architecture

- **`main.py`**: FastAPI entry point. It wraps the `root_agent` from `app/agent.py`.
- **`app/`**: Contains the ADK agent logic, tools, and multimodal generation code (merged from `deep-search`).
- **`static/`**: Stores generated files (audio, video, slides).
- **Frontend**: React + Vite + Tailwind CSS.

