import os
import logging
import sys
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from app.core.config import STATIC_DIR, DOCS_DIR, BUCKET_NAME
from app.api import research, threads, session, radars, exploration, projects, user, activities

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure the current directory is in sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Logging startup
    logger.info("Application startup complete.")
    
    # Start Background Scheduler for Radars
    from app.services.scheduler import start_scheduler
    start_scheduler()

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(radars.router, prefix="/api/radars", tags=["Radars"])
app.include_router(threads.router, prefix="/api/threads", tags=["Threads"]) # /api/threads
app.include_router(session.router, prefix="/api/session", tags=["Session"]) # /api/session/{session_id}
app.include_router(exploration.router, prefix="/api/exploration", tags=["Exploration"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(user.router, prefix="/api/user", tags=["User"])
app.include_router(activities.router, prefix="/api/activities", tags=["Activities"])

@app.get("/static/{folder}/{filename}")
async def serve_static_content(folder: str, filename: str):
    """
    Intercepts static content requests (docs, audio, slides, videos) to lazily restore 
    them from GCS if missing from local ephemeral disk.
    """
    if folder not in ["docs", "audio", "slides", "videos"]:
        raise HTTPException(status_code=403, detail="Invalid folder access")

    # Mapping URI folder to local directory
    folder_map = {
        "docs": DOCS_DIR,
        "audio": os.path.join(STATIC_DIR, "audio"),
        "slides": os.path.join(STATIC_DIR, "slides"),
        "videos": os.path.join(STATIC_DIR, "videos")
    }
    
    target_dir = folder_map.get(folder)
    # Ensure dir exists locally
    os.makedirs(target_dir, exist_ok=True)
    
    local_path = os.path.join(target_dir, filename)
    
    # Sanity check for path traversal
    if not os.path.abspath(local_path).startswith(os.path.abspath(target_dir)):
        raise HTTPException(status_code=403, detail="Invalid path")
    
    # 1. Check Local
    if os.path.exists(local_path):
        return FileResponse(local_path)

    # 2. Try Restore from GCS
    try:
        from google.cloud import storage
        client = storage.Client()
        # Ensure BUCKET_NAME is set
        bucket_name = os.getenv("GCS_BUCKET_NAME") or os.getenv("VITE_FIREBASE_STORAGE_BUCKET") or f"{os.getenv('GOOGLE_CLOUD_PROJECT')}-aletheia-docs"
        
        if bucket_name:
            bucket = client.bucket(bucket_name)
            # GCS Path: e.g. "audio/filename.mp3"
            blob_name = f"{folder}/{filename}"
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                logger.info(f"Restoring {blob_name} from GCS to {local_path}")
                blob.download_to_filename(local_path)
                return FileResponse(local_path)
            else:
                logger.warning(f"File not found in GCS: {blob_name}")
    except Exception as e:
        logger.error(f"Failed to restore {folder}/{filename} from GCS: {e}")
            
    # 3. 404
    raise HTTPException(status_code=404, detail="File not found")

# Mount Static Files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve Frontend (Production / Dist)
if os.path.exists("dist"):
    logger.info("Serving production frontend from 'dist' directory.")
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Explicitly check if the file exists in the 'dist' directory
        dist_file_path = os.path.join("dist", full_path)
        if full_path and os.path.isfile(dist_file_path):
            return FileResponse(dist_file_path)
            
        # API/Static fall-through check
        if full_path.startswith("api/") or full_path.startswith("static/"):
            logger.warning(f"Static/API request fall-through to catch-all: {full_path}")
            raise HTTPException(status_code=404, detail=f"The requested asset '{full_path}' was not found.")
        
        # SPA fallback
        index_path = "dist/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
        return HTTPException(status_code=404, detail="Application entry point (index.html) not found.")
else:
    logger.warning("'dist' directory not found. Frontend will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
