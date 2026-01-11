import os
import logging
import uuid
import base64
import datetime
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure the current directory is in sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ADK and Application Imports
from google.adk.runners import Runner
from google.genai import types
from app.agent import app as adk_app
from app.schemas import ResearchRequest, ResearchResponse, FileItem
from app.auth import get_current_user
from app.sessions import get_session_service

# Initialize session service
session_service = get_session_service()

app = FastAPI()

# Mount static files directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/research", response_model=ResearchResponse)
async def research_endpoint(request: ResearchRequest, user_id: str = Depends(get_current_user)):
    logger.info(f"Received research request from {user_id}: {request.query}")
    try:
        runner = Runner(app=adk_app, session_service=session_service)
        session_id = request.sessionId or str(uuid.uuid4())
        
        # Check if session exists, if not create it
        session_exists = False
        try:
            existing_session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
            if existing_session:
                session_exists = True
                logger.info(f"Reusing existing session: {session_id}")
        except Exception as e:
            logger.warning(f"Error while checking for existing session {session_id}: {e}")

        if not session_exists:
            try:
                logger.info(f"Initializing session: {session_id}")
                await session_service.create_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
            except Exception:
                logger.exception(f"Error initializing session: {session_id}")
                raise
        
        # Save the query as the title if this is a fresh session
        try:
            curr = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
            if not curr.state or "title" not in curr.state:
                await session_service.update_session(
                    user_id=user_id, 
                    session_id=session_id, 
                    app_name=adk_app.name,
                    state_update={
                        "title": request.query[:50] + ("..." if len(request.query) > 50 else "")
                    }
                )
        except Exception:
            logger.exception(f"Error setting session title for session: {session_id}")

        # Construct content object
        parts = [types.Part(text=request.query)]
        for f in request.files:
            try:
                file_bytes = base64.b64decode(f.data)
                parts.append(types.Part(inline_data=types.Blob(mime_type=f.mime_type, data=file_bytes)))
                logger.info(f"Added file to request: {f.name} ({f.mime_type})")
            except Exception as e:
                logger.error(f"Failed to process file {f.name}: {e}")
                
        content = types.Content(parts=parts)

        # Execute runner
        async for _ in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            pass # We just consume the events to let the agent complete

        # Retrieve the updated session to get the final response
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        
        response_text = ""
        generated_files = []
        
        if session and session.events:
            # The last event from the assistant is usually the final response
            # We look for the most recent message with a role or content
            last_message_event = None
            for event in reversed(session.events):
                if getattr(event, "role", None) == "assistant" or (hasattr(event, "content") and event.content):
                    last_message_event = event
                    break
            
            if last_message_event:
                # Extract text using the same logic as get_session_history
                content_attr = getattr(last_message_event, "content", None)
                if content_attr and hasattr(content_attr, "parts") and content_attr.parts:
                    response_text = "\n".join([getattr(p, "text", "") for p in content_attr.parts if getattr(p, "text", "")])
                
                if not response_text:
                    response_text = getattr(last_message_event, "text", "") or getattr(last_message_event, "output", "") or ""

            # Collect any generated files from the session state
            if session.state and isinstance(session.state, dict):
                generated_files = session.state.get("generated_files", [])

        # Map generated files to FileItem
        files = []
        for f in generated_files:
            filename = os.path.basename(f)
            file_type = "presentation" if filename.endswith(".pptx") else "audio" if filename.endswith(".mp3") else "video"
            files.append(FileItem(
                path=f"/static/{filename}",
                type=file_type,
                name=filename
            ))
            
        logger.info(f"Request processed. Found {len(files)} files.")
        return ResearchResponse(content=response_text, files=files)

    except Exception as e:
        logger.error(f"Error processing research request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/threads")
async def get_user_threads(user_id: str = Depends(get_current_user)):
    try:
        threads = []
        session_list_fn = getattr(session_service, "list_sessions_for_user", None)
        if callable(session_list_fn):
            sessions = await session_list_fn(user_id=user_id, app_name=adk_app.name)
            for s in sessions or []:
                if isinstance(s, dict):
                    raw_state = s.get("state") or {}
                    session_id = s.get("session_id") or s.get("id")
                    title = raw_state.get("title") or s.get("title") or "Untitled Research"
                else:
                    raw_state = getattr(s, "state", None) or {}
                    session_id = getattr(s, "session_id", None) or getattr(s, "id", None)
                    title = (raw_state.get("title") if isinstance(raw_state, dict) else None) or getattr(s, "title", None) or "Untitled Research"

                if session_id:
                    threads.append({"id": session_id, "title": title})
            return {"threads": threads}
        return {"threads": []}
    except Exception as e:
        logger.error(f"Error fetching threads: {e}")
        return {"threads": []}

@app.get("/api/session/{session_id}")
async def get_session_history(session_id: str, user_id: str = Depends(get_current_user)):
    try:
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        if not session:
            return {"messages": []}
        
        history = []
        for event in session.events:
            text = ""
            content = getattr(event, "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    text = "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", "")])
            
            if not text:
                text = getattr(event, "text", "") or getattr(event, "output", "") or ""
            
            if not text or not str(text).strip():
                continue
            
            # Improved role detection for ADK Events
            role = None
            
            # 1. Check direct 'author' attribute (common in ADK Event objects)
            author = getattr(event, "author", None)
            if author:
                author_str = str(author).lower()
                if "user" in author_str:
                    role = "user"
                elif any(m in author_str for m in ("assistant", "model", "aletheia")):
                    role = "assistant"
                elif "system" in author_str:
                    role = "system"
                elif "tool" in author_str:
                    role = "tool"

            # 2. Check 'role' attribute if 'author' didn't yield a standard role
            if not role:
                role = getattr(event, "role", None)
                if isinstance(role, str):
                    role = role.lower()
            
            # 3. Check within content (Gemini type events)
            if not role and content:
                role = getattr(content, "role", None)
                if isinstance(role, str):
                    role = role.lower()

            # 4. Final heuristic fallback
            if role not in ("user", "assistant", "system", "tool"):
                event_type = str(getattr(event, "type", "") or getattr(event, "event_type", "")).lower()
                if any(k in event_type for k in ("user", "input", "request")):
                    role = "user"
                elif "thought" in text.lower() or "thinking" in event_type:
                    role = "system"
                else:
                    role = "assistant"
            
            history.append({
                "id": str(event.id),
                "role": role,
                "content": text,
                "timestamp": event.timestamp
            })
            
        return {"messages": history}
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}", exc_info=True)
        return {"messages": []}

# Serve Frontend
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path.startswith("static"):
            raise HTTPException(status_code=404)
        path = os.path.join("dist", full_path)
        if os.path.isfile(path):
            from fastapi.responses import FileResponse
            return FileResponse(path)
        from fastapi.responses import FileResponse
        return FileResponse("dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
