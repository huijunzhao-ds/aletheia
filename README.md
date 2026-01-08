
# Aletheia | Multimedia Research Assistant

A modern research interface separated into a React frontend and a Python backend (ADK-compatible). 


## 1. Run the App Locally

## Prerequisites

- **Python 3.10+** (managed via uv)
- **Node.js** (for frontend development)
- **Google Gemini API Key** (set in `.env` as `GOOGLE_API_KEY`)
- **uv**: [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

### Environment Setup

Create a `.env` file in the **root directory** of the project (`aletheia/.env`) with the following content:

```env
GOOGLE_API_KEY="your-google-gemini-api-key"
```

### Backend Setup (Python)

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

### Frontend Setup

The frontend is a React application built with Vite.

```bash
# 1. Install dependencies
npm install

# 2. Run the development server
npm run dev
```

Open the URL shown in the terminal (usually `http://localhost:3000`) to interact with Aletheia.

## 2. Deploy to Cloud Run

Aletheia is configured for deployment to **Google Cloud Run** using **GitHub Actions**. The latest version is deployed to `https://aletheia-356306.uc.r.appspot.com/`.

### Google Cloud Setup
1. **Enable APIs**: Create a new GCP Project and enable Cloud Run, Artifact Registry, and Cloud Build APIs. Can use CLI: `gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com`
2. **Artifact Registry**: Create a Docker repository named `aletheia` in `us-central1`. Can use CLI: `gcloud artifacts repositories create aletheia --repository-format=docker --location=us-central1`
3. **Service Account**: Create a Service Account with `Cloud Run Admin` and `Artifact Registry Writer` roles. Generate a JSON key. Can use CLI: `gcloud iam service-accounts create aletheia --display-name "Aletheia Service Account"`
4. **Service Account Key**: Generate a JSON key for the Service Account. Can use CLI: `gcloud iam service-accounts keys create aletheia.json --iam-account aletheia@aletheia-356306.iam.gserviceaccount.com`    

### GitHub Secrets
Add the following secrets to your GitHub repository (Settings > Secrets and variables > Actions):
- `GCP_SA_KEY`: The JSON key of your Service Account.
- `GOOGLE_API_KEY`: Your Gemini API Key (needed for the agent to run in the cloud).

Every time the branch `feature/cloud_deploy` is updated, GitHub Actions will deploy the latest version to Cloud Run automatically. Suggested to test locally before merging to `feature/cloud_deploy`.

### Manual Deployment (via CLI)
If you prefer to deploy manually:
```bash
gcloud run deploy aletheia --source . --region us-central1 --set-env-vars GOOGLE_API_KEY=your_key
```

## 3. Architecture

- **`main.py`**: FastAPI entry point. It wraps the `root_agent` from `app/agent.py`.
- **`app/`**: Contains the ADK agent logic, tools, and multimodal generation code (merged from `deep-search`).
- **`static/`**: Stores generated files (audio, video, slides).
- **Frontend**: React + Vite + Tailwind CSS.

## 4. Development Notes and Contribution Guidelines

- **Multimedia**: The application uses `ffmpeg` for video generation. The provided `Dockerfile` automates this installation.
- **Frontend/Backend Integration**: In production, the FastAPI server serves the React frontend from the `dist` directory. Running `npm run build` locally is recommended before building the Docker image.
- **Version Control**: Use `uv` for Python dependencies and `npm` for Node.js dependencies.
- How to Contribute: 
    - Fork/clone the repository
    - Create a new branch and make your changes
    - Commit your changes and push to your branch
    - Merge into `feature/cloud_deploy` first and GitHub Actions will deploy to Cloud Run automatically. If it works as expected, create a pull request and merge into `main`.

## 4. TO-DOs

- [x] Deploy to GCP Cloud Run using GitHub Actions CI/CD
- [ ] Add user login and authentication (WIP)
- [ ] Update UI/UX
- [ ] Test and improve chat features
- [ ] Test and improve audio features
- [ ] Test and improve presentation features
- [ ] Test and improve video features
- [ ] Add memory management and personalization


