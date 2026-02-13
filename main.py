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
from app.api import research, threads, session, radars, exploration, projects, user

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

# Static Docs Lazy Restore Handler
@app.get("/static/docs/{filename}")
async def serve_doc(filename: str):
    """
    Intercepts static doc requests to lazily restore them from GCS if missing from local ephemeral disk.
    """
    local_path = os.path.join(DOCS_DIR, filename)
    
    if not os.path.exists(local_path):
        # Lazy Restore from GCS
        try:
            from app.core.session_storage import get_storage_client
            # BUCKET_NAME imported from config
            client = get_storage_client()
            if client and BUCKET_NAME:
                bucket = client.bucket(BUCKET_NAME)
                blob_name = f"docs/{filename}"
                blob = bucket.blob(blob_name)
                
                if blob.exists():
                    logger.info(f"Restoring requested doc from GCS: {blob_name}")
                    blob.download_to_filename(local_path)
        except Exception as e:
            logger.error(f"Failed to restore {filename} for serving: {e}")

    if os.path.exists(local_path):
        return FileResponse(local_path)
    
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
