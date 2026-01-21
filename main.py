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

# Static files setup with absolute paths for cloud safety
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOCS_DIR = os.path.join(STATIC_DIR, "docs")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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

        # Construct content object and persist files for history
        parts = [types.Part(text=request.query)]
        uploaded_doc_metadata = []
        
        for f in request.files:
            try:
                file_bytes = base64.b64decode(f.data)
                
                # Persist to static/docs/ with absolute path for cloud reliability
                safe_name = "".join([c if c.isalnum() or c in ".-_" else "_" for c in f.name])
                filename = f"{session_id}_{safe_name}"
                file_abs_path = os.path.join(DOCS_DIR, filename)
                
                with open(file_abs_path, "wb") as bf:
                    bf.write(file_bytes)
                
                if os.path.exists(file_abs_path):
                    logger.info(f"Successfully persisted file to disk: {file_abs_path}")
                else:
                    logger.error(f"Failed to find file on disk after write attempt: {file_abs_path}")
                
                url_path = f"/static/docs/{filename}"
                uploaded_doc_metadata.append({
                    "name": f.name,
                    "path": url_path,
                    "type": "pdf" if f.name.lower().endswith(".pdf") else "other"
                })
                
                parts.append(types.Part(inline_data=types.Blob(mime_type=f.mime_type, data=file_bytes)))
                logger.info(f"Added and persisted file: {f.name} ({f.mime_type})")
            except Exception as e:
                logger.error(f"Failed to process/persist file {f.name}: {e}")
                
        # Update session state with persisted file metadata
        if uploaded_doc_metadata:
            try:
                curr_session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
                existing_uploaded = curr_session.state.get("uploaded_files", [])
                # Deduplicate by path
                existing_paths = {uf.get("path") for uf in existing_uploaded if isinstance(uf, dict)}
                for doc in uploaded_doc_metadata:
                    if doc["path"] not in existing_paths:
                        existing_uploaded.append(doc)
                
                await session_service.update_session(
                    user_id=user_id,
                    session_id=session_id,
                    app_name=adk_app.name,
                    state_update={"uploaded_files": existing_uploaded}
                )
            except Exception as e:
                logger.error(f"Failed to update session with uploaded file metadata: {e}")

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
        
        # Prepare pools for matching files to messages
        history = []
        gen_files = session.state.get("generated_files", []) or []
        uploaded_files = session.state.get("uploaded_files", []) or []
        unassigned_uploads = list(uploaded_files)
        unassigned_generated = list(gen_files)
        
        logger.info(f"Loading history for session {session_id}. State has {len(uploaded_files)} uploads and {len(gen_files)} generated files.")
        
        for event in session.events:
            text = ""
            content = getattr(event, "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    # Filter out the scrubbed file placeholder from the UI text
                    text_parts = []
                    for p in parts:
                        p_text = getattr(p, "text", "")
                        # Handle potential None value from valid but empty attribute
                        p_text_str = str(p_text or "")
                        if p_text_str and "[External file data not preserved in history]" not in p_text_str:
                            text_parts.append(p_text_str)
                    text = "\n".join(text_parts)
            
            if not text:
                # Still check event level text but filter placeholder
                raw_text = getattr(event, "text", "") or getattr(event, "output", "") or ""
                if "[External file data not preserved in history]" not in str(raw_text):
                    text = raw_text
            
            # If after filtering there is no text AND no files (checked later), we might still want to show the bubble
            # if it was an upload-only message.
            
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
            
            # Extract files if any
            files = []
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    for p in parts:
                        if hasattr(p, "inline_data"):
                            # This is an uploaded file
                            # Note: Data might be scrubbed, but we still want the name/type
                            # For now, we can only reasonably restore generated files with paths
                            pass
            
            # ADK often stores generated files in session.state['generated_files']
            # We'll check if this specific event (if it's the final assistant response) 
            # matches the generated files.
            
            # Match files to this specific message using consumption logic
            msg_files = []
            
            # 1. Match Uploaded Files (User role)
            # We count scrubbed parts to know how many files to pull from the session pool
            if role == "user" and content:
                scrubbed_count = 0
                for p in getattr(content, "parts", []):
                    p_val = getattr(p, "text", "")
                    if "[External file data not preserved in history]" in str(p_val or ""):
                        scrubbed_count += 1
                
                for _ in range(scrubbed_count):
                    if unassigned_uploads:
                        up = unassigned_uploads.pop(0)
                        if isinstance(up, dict):
                            msg_files.append({
                                "path": up.get("path"),
                                "type": "pdf" if up.get("path", "").lower().endswith(".pdf") else "other",
                                "name": up.get("name")
                            })

            # 2. Match Generated Files (Assistant role)
            # Usually assistant responses follow a tool call that generates files.
            # If the response text mentions synthesis or files, we assign from the generated pool.
            if role == "assistant":
                # Heuristic: if this is a synthesis message, it likely corresponds to the latest generated files
                # For now, if we have unassigned generated files, we assign them to the next assistant message
                if unassigned_generated:
                    # Assistant messages usually come one by one after Turn/Tool events.
                    # We'll take ALL currently unassigned generated files if this message looks final.
                    if text.strip() == "Research synthesis complete." or "report" in text.lower():
                        while unassigned_generated:
                            f = unassigned_generated.pop(0)
                            path = f if isinstance(f, str) else f.get("path")
                            name = os.path.basename(path) if isinstance(f, str) else f.get("name", os.path.basename(path))
                            msg_files.append({
                                "path": path if path.startswith("/") or "://" in path else f"/{path}",
                                "type": "pdf" if path.lower().endswith(".pdf") else "other",
                                "name": name
                            })

            # Skip messages with no text AND no files (unless it's a thinking placeholder, which we don't handle here yet)
            if not text.strip() and not msg_files:
                continue

            history.append({
                "id": str(event.id),
                "role": role,
                "content": text,
                "timestamp": event.timestamp,
                "files": msg_files
            })
            
        # Collect all session-wide documents
        all_docs = []
        # 1. From generated files
        for f in gen_files:
            path = f if isinstance(f, str) else f.get("path")
            name = os.path.basename(path) if isinstance(f, str) else f.get("name", os.path.basename(path))
            
            if path and (path.lower().endswith(".pdf") or (isinstance(f, dict) and f.get("type") == "pdf")):
                all_docs.append({
                    "name": name,
                    "url": path if path.startswith("/") or "://" in path else f"/{path}"
                })
        
        # 2. From specifically tracked uploaded files
        for f in uploaded_files:
            if isinstance(f, dict) and f.get("type") == "pdf":
                path = f.get("path")
                all_docs.append({
                    "name": f.get("name"),
                    "url": path if path.startswith("/") or "://" in path else f"/{path}"
                })

        return {
            "messages": history,
            "documents": all_docs
        }
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}", exc_info=True)
        return {"messages": []}

# Serve Frontend
if os.path.exists("dist"):
    logger.info("Serving production frontend from 'dist' directory.")
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Explicitly check if the file exists in the 'dist' directory
        # This handles assets like favicon.ico, manifest.json, etc.
        dist_file_path = os.path.join("dist", full_path)
        if full_path and os.path.isfile(dist_file_path):
            from fastapi.responses import FileResponse
            return FileResponse(dist_file_path)
            
        # If it's an API or Static path that reached here, it means the specific 
        # routes/mounts didn't catch it. We should 404 instead of returning index.html
        if full_path.startswith("api/") or full_path.startswith("static/"):
            logger.warning(f"Static/API request fall-through to catch-all: {full_path}")
            raise HTTPException(status_code=404, detail=f"The requested asset '{full_path}' was not found.")
        
        # SPA fallback: Send index.html for any other route to let React handle it
        from fastapi.responses import FileResponse
        index_path = "dist/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
        return HTTPException(status_code=404, detail="Application entry point (index.html) not found.")
else:
    logger.warning("'dist' directory not found. Frontend will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
