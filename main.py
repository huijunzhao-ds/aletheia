import os
import re
import logging
import uuid
from typing import List
from google.genai import types
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure the current directory is in sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

session_service = InMemorySessionService()

# Import the ADK agent app
try:
    from app.agent import app as adk_app
except ImportError as e:
    logger.error(f"Failed to import app.agent: {e}")
    raise

app = FastAPI()

# Mount static files directory
# Ensure directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the built frontend (Vite's default output is 'dist')
# Note: In the Dockerfile, we will build the React app and place it in the 'dist' folder
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent intercepting API routes
        if full_path.startswith("api/") or full_path.startswith("static/"):
            raise HTTPException(status_code=404)
        
        # Check if file exists in dist
        path = os.path.join("dist", full_path)
        if os.path.isfile(path):
            from fastapi.responses import FileResponse
            return FileResponse(path)
            
        # Fallback to index.html for SPA routing
        from fastapi.responses import FileResponse
        return FileResponse("dist/index.html")

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    query: str
    mode: str = "quick"

class FileItem(BaseModel):
    path: str
    type: str  # 'audio', 'video', 'presentation'
    name: str

class ResearchResponse(BaseModel):
    content: str
    files: List[FileItem]

@app.post("/api/research", response_model=ResearchResponse)
async def research_endpoint(request: ResearchRequest):
    logger.info(f"Received research request: {request.query} (mode: {request.mode})")
    try:
        # Depending on the mode, we might want to adjust the prompt or agent config,
        # but for now we pass the query to the root agent.
        # The deep-search agent is designed to route automatically.
        
        # Invoke the agent using the ADK Runner
        runner = Runner(app=adk_app, session_service=session_service)
        
        user_id = "default_user"
        session_id = str(uuid.uuid4())
        
        # Construct content object
        content = types.Content(parts=[types.Part(text=request.query)])
        
        # Explicitly create session before running
        await session_service.create_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)

        # Execute runner and consume generator
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            pass # We just consume it to let the agent finish
        
        # Retrieve the session to get the full history/response
        # Note: In a real app, you might want closer inspection of events, but getting the last message is a good heuristic for "answer"
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        
        response_text = ""
        if session and session.events:
            last_event = session.events[-1]
            if hasattr(last_event, 'content') and hasattr(last_event.content, 'parts'):
                parts = last_event.content.parts
                if parts:
                    response_text = parts[0].text or ""
            elif hasattr(last_event, 'text'):
                 response_text = last_event.text or ""
            elif hasattr(last_event, 'output'):
                 response_text = last_event.output or ""
        
        # Extract generated files from the response text or side-effects.
        # Since the tools return paths that the LLM likely includes in the text,
        # we scan the text for file paths in the static directory.
        
        files = []
        # Pattern to match paths like static/audio/uuid.mp3, static/videos/uuid.mp4, static/slides/uuid.pptx
        # We look for static/... followed by allowed extensions
        pattern = r"(static/(audio|videos|slides)/[\w-]+\.(mp3|mp4|pptx|png))"
        matches = re.findall(pattern, response_text)
        
        # Deduplicate matches
        unique_paths = set()
        
        for full_path, folder, ext in matches:
            if full_path in unique_paths:
                continue
            unique_paths.add(full_path)
            
            # Determine type based on folder
            file_type = "other"
            if folder == "audio":
                file_type = "audio"
            elif folder == "videos":
                file_type = "video"
            elif folder == "slides":
                file_type = "presentation"
            
            filename = os.path.basename(full_path)
            
            files.append(FileItem(
                path=full_path,
                type=file_type,
                name=filename
            ))
            
        logger.info(f"Request processed. Found {len(files)} files.")
        
        return ResearchResponse(
            content=response_text,
            files=files
        )

    except Exception as e:
        logger.error(f"Error processing research request: {e}", exc_info=True)
        # Return a 500 with the error message
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
