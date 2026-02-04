
# Aletheia | Multimedia Research Assistant

A modern research interface separated into a React frontend and a Python backend (ADK-compatible). 


## 1. Run the App Locally

## Prerequisites

- **Python 3.10+** (managed via [uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js** (for frontend development)
- **Google Gemini API Key** (set in `.env` as `GOOGLE_API_KEY`)

### Environment Setup

Create a `.env` file in the **root directory** of the project (`aletheia/.env`) with the following content:

```env
GOOGLE_API_KEY="your-google-gemini-api-key"
```

### Backend Setup

The backend is built with FastAPI and Google's Agent Development Kit (ADK).

```bash
# 1. Create virtual environment
uv venv .venv

# 2. Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies - only need to run once
uv pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload --port 8000
```
The backend will start at `http://localhost:8000`. 

### Frontend Setup

The frontend is a React application built with Vite.

```bash
# 1. Install dependencies - only need to run once
npm install

# 2. Run the development server
npm run dev
```

Open the URL shown in the terminal (usually `http://localhost:3000`) to interact with Aletheia.

## 2. Deploy to Cloud Run

Aletheia is configured for deployment to **Google Cloud Run** using **GitHub Actions**. The latest version is deployed to `https://aletheia-635800011324.us-central1.run.app/`.

### Google Cloud Setup
1. **Enable APIs**: Create a new GCP Project and enable Cloud Run, Artifact Registry, and Cloud Build APIs. Can use CLI
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```
2. **Artifact Registry**: Create a Docker repository named `aletheia` in `us-central1`. Can use CLI
```bash
gcloud artifacts repositories create aletheia --repository-format=docker --location=us-central1
```
3. **Service Account**: Create a Service Account with `Cloud Run Admin` and `Artifact Registry Writer` roles. Generate a JSON key. Can use CLI
```bash
gcloud iam service-accounts create aletheia --display-name "Aletheia Service Account"
```
4. **Service Account Key**: Generate a JSON key for the Service Account. Can use CLI
```bash
gcloud iam service-accounts keys create aletheia.json --iam-account aletheia@aletheia-356306.iam.gserviceaccount.com
```

### GitHub Secrets
Add the following secrets to your GitHub repository (Settings > Secrets and variables > Actions):
- `GCP_SA_KEY`: The JSON key of your Service Account.
- `GOOGLE_API_KEY`: Your Gemini API Key.
- `VITE_FIREBASE_API_KEY`: From Firebase Console.
- `VITE_FIREBASE_AUTH_DOMAIN`: From Firebase Console.
- `VITE_FIREBASE_PROJECT_ID`: From Firebase Console.
- `VITE_FIREBASE_STORAGE_BUCKET`: From Firebase Console.
- `VITE_FIREBASE_MESSAGING_SENDER_ID`: From Firebase Console.
- `VITE_FIREBASE_APP_ID`: From Firebase Console.

### Authentication & Database Setup (Firebase)
1. Go to [Firebase Console](https://console.firebase.google.com/) and create a new project.
2. **Authentication**: Enable the **Google** sign-in provider.
3. **Firestore Database**: Click "Create Database" in **production mode** (Firestore in Native mode, the default). This provides permanent storage for your research history.
4. **Local Credentials**: For the backend to access Firestore locally, run:
   ```bash
   gcloud auth application-default login
   ```
5. Register a Web App to get your `firebaseConfig` keys.
6. In your `.env` file, add:
   ```env
   VITE_FIREBASE_API_KEY="AIza..."
   VITE_FIREBASE_AUTH_DOMAIN="your-app.firebaseapp.com"
   VITE_FIREBASE_PROJECT_ID="your-app"
   VITE_FIREBASE_STORAGE_BUCKET="your-app.appspot.com"
   VITE_FIREBASE_MESSAGING_SENDER_ID="..."
   VITE_FIREBASE_APP_ID="..."
   ENV="development"
   ```
7. **Configure Firestore Security Rules**: Restrict read/write access to authenticated users and only to their own data. For example, if you store user-specific session or history documents under a `sessions` collection with a `userId` field equal to the authenticated user's `uid`, you can use rules like:
   ```txt
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       // Example: user sessions/history stored in /sessions/{sessionId}
       match /sessions/{sessionId} {
         allow read, write: if request.auth != null
           && request.auth.uid == resource.data.userId;
       }
     }
   }
   ```
   Apply these rules in the **Firestore -> Rules** tab in the Firebase Console, or via the Firebase CLI if you manage rules as code. Adjust collection names and fields (`sessions`, `userId`) to match your actual data model.

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

## 5. TO-DOs

- [x] Deploy to GCP Cloud Run using GitHub Actions CI/CD
- [x] Add user login and authentication 
- [x] Implement radar features
- [x] Implement exploration features
- [ ] Implement projects features (WIP)
- [ ] Add a user help agent
- [ ] Add presentation features
- [ ] Add video features
- [ ] Add personal knowledge and information sources
- [ ] Add memory management and personalization
- [ ] Add social and share features



