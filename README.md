
# Aletheia | Multimedia Research Assistant

Aletheia is an advanced, AI-powered multimedia research assistant designed to accelerate discovery and knowledge synthesis. Built with a modern React frontend and a Python backend adaptable to Google's Agent Development Kit (ADK), Aletheia employs a multi-agent orchestration pattern to help users not just search, but deeply explore topics. 

Whether you are tracking emerging trends with automated **Research Radars**, deep-diving into academic papers with the **Exploration** interface, or generating multi-modal outputs like audio podcasts and briefings for your research **Projects**, Aletheia serves as your intelligent partner in navigating the world's information. 


## 1. Run the App Locally

## Prerequisites

- **Python 3.10+** (managed via [uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js** (for frontend development)
- **Google Gemini API Key** (set in `.env` as `GOOGLE_API_KEY`)
- **Google Cloud Platform (GCP) Credentials**:
    - A Service Account key (`gcp-sa-key.json`) with permissons for Firestore and Cloud Storage.

### Environment Setup

Create a `.env` file in the **root directory** of the project (`aletheia/.env`) with the following content:

```env
GOOGLE_API_KEY="your-google-gemini-api-key"
```

### Backend Setup

The backend is built with FastAPI and Google's Agent Development Kit (ADK).

```bash
# 1. Create virtual environment - only need to run once
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

Aletheia is configured for deployment to **Google Cloud Run** and **Firebase** using **GitHub Actions**. 

The latest prod version is deployed to `https://aletheia-635800011324.us-central1.run.app/`, with the code in main branch.

The latest QA version is deployed to `https://aletheia-qa-635800011324.us-central1.run.app/`, with the code in develop branch.


## 3. Architecture

Aletheia uses a **multi-agent orchestration** pattern powered by Google's ADK and Gemini 2.5.

- **`root_agent` (Router)**: The main entry point that analyzes user intent and routes tasks to specialists.
- **Specialist Agents**:
    - **`research_radar_specialist`**: Manages "Research Radars" (automated recurring research feeds) and handles questions about specific radars.
    - **`exploration_specialist`**: Handles general queries and browsing. It has access to your "To Review" list (saved papers) to provide context-aware answers.
    - **`search_specialist`**: Performs deep multi-step web and academic research using Google Search and Arxiv.
    - **`project_specialist`** *(WIP)*: Manages long-term research projects and artifacts.
- **Multimedia Generation**: Dedicated tools for generating audio podcasts, markdown reports, and (future) video/slides.
- **Backend Services**:
    - **FastAPI**: Handles API requests and routing (`app/api/`).
    - **Firestore**: Stores user data, radar configurations, and session history (`app/db.py`).
    - **Cloud Storage**: Persists uploaded files and generated reports (`app/storage.py`).
    - **APScheduler**: Manages background jobs and scheduled radar syncs (`app/services/scheduler.py`).
- **Frontend**: React + Vite + Tailwind CSS with a responsive Sidebar UI.

## 4. Key Features & UI Guide

- **Dashboard**: High-level overview of your research activities.
- **Research Radar**: Create automated agents that monitor specific topics (e.g., "GenAI Trends") hourly/daily/weekly/monthly and generate multimedia digests.
- **Exploration**: A chat-first interface for deep-diving into topics.
    - **To Review**: Articles and papers you've saved for later reading. The AI has direct access to these.
    - **Outputs**: Generated assets like Audio Podcasts, Markdown Reports, and so on.
    - **Reviewed**: Archive of papers you've finished reading.
    - **My Chats**: History of your research conversations.
- **Projects** *(Coming Soon)*: Organize your research into structured collections.

## 5. How to Contribute

  - Fork/clone the repository
  - Create a new branch and make your changes
  - Commit your changes and push to your branch
  - Merge into `develop` first and GitHub Actions will deploy to qa environment automatically. If it works as expected, create a pull request into `main`. 
  - After owner reviews and approves, the PR can be merged into `main` and the qa environment will be deployed to production environment automatically.

## 6. TO-DOs

- [x] Deploy to GCP Cloud Run using GitHub Actions CI/CD
- [x] Add user login and authentication 
- [x] Implement radar and exploration features
- [ ] Enhance radar search and ranking
    - search query (done)
    - ordering of initial search results (done)
    - refine selection of papers (done)
    - ranking according to semantic similarity to radar title and description (done)
    - parallel summary generation for multiple papers (done)
    - next level ranking according to user preferences - build user profile summary (WIP)
    - why user interested in this paper - add to summary

- [ ] Enhance exploration chat context management
- [ ] Implement projects features 
- [ ] Add a user help agent
- [ ] Add presentation features
- [ ] Add video features
- [ ] Add personal knowledge and information sources
- [ ] Add memory management and personalization
- [ ] Add social and share features
