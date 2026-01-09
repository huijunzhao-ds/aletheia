import os
import re
import logging
import uuid
from google.genai import types
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import sys
import base64
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure the current directory is in sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
import datetime
from typing import List, Optional, Any, Dict
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.in_memory_session_service import InMemorySessionService

def scrub_blobs(obj):
    """
    Recursively removes large binary data (base64 strings) from the session 
    to stay within Firestore's 1MB document limit.
    """
    if isinstance(obj, dict):
        if "inline_data" in obj and isinstance(obj["inline_data"], dict):
            blob = obj["inline_data"]
            if "data" in blob and isinstance(blob["data"], str) and len(blob["data"]) > 1024:
                # Use a valid base64 placeholder to avoid Pydantic validation errors on reload
                # 'REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ==' is base64 for 'DATA_STRIPPED_FOR_STORAGE'
                blob["data"] = "REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ=="
        return {k: scrub_blobs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [scrub_blobs(x) for x in obj]
    return obj

def rescue_blobs(obj):
    """
    Cleans up legacy invalid base64 placeholders to prevent validation crashes.
    """
    if isinstance(obj, dict):
        if "inline_data" in obj and isinstance(obj["inline_data"], dict):
            blob = obj["inline_data"]
            if "data" in blob and isinstance(blob["data"], str) and blob["data"].startswith("[Data stripped"):
                blob["data"] = "REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ=="
        return {k: rescue_blobs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [rescue_blobs(x) for x in obj]
    return obj

class FirestoreSessionService(BaseSessionService):
    """
    Custom Firestore-backed session service for Aletheia.
    Provides persistence for research threads and conversation history.
    """
    def __init__(self, collection_name="sessions"):
        try:
            from google.cloud import firestore
            self.db = firestore.AsyncClient()
            self.collection_name = collection_name
            self.firestore_module = firestore
        except ImportError:
            logger.error("google-cloud-firestore not installed. FirestoreSessionService will not work.")
            raise

    async def get_session(self, *, user_id: str, session_id: str, app_name: str) -> Optional[Session]:
        doc = await self.db.collection(self.collection_name).document(session_id).get()
        if doc.exists:
            data = doc.to_dict()
            if data.get("user_id") == user_id and data.get("app_name") == app_name:
                # Deserialize events if they are stored as a JSON string
                events_data = data.get("events")
                if isinstance(events_data, str):
                    try:
                        data["events"] = json.loads(events_data)
                    except Exception as e:
                        logger.error(f"Failed to parse stringified events: {e}")
                        data["events"] = []
                # Rescue legacy invalid base64 strings
                data = rescue_blobs(data)
                return Session.model_validate(data)
        return None

    async def create_session(self, *, user_id: str, session_id: str, app_name: str, state: Optional[Dict[str, Any]] = None, **kwargs) -> Session:
        session = Session(
            id=session_id,
            user_id=user_id,
            app_name=app_name,
            state=state or {},
            events=[],
            last_update_time=datetime.datetime.now(datetime.timezone.utc).timestamp()
        )
        data = session.model_dump(mode='json', exclude_none=True)
        # Scrub large blobs to stay under 1MB limit
        data = scrub_blobs(data)
        # Stringify events to bypass Firestore's nested array limitation
        data["events"] = json.dumps(data.get("events", []))
        await self.db.collection(self.collection_name).document(session_id).set(data)
        return session

    async def append_event(self, *, session: Session, event: Event) -> Event:
        session.events.append(event)
        ts = event.timestamp or datetime.datetime.now(datetime.timezone.utc)
        if hasattr(ts, 'timestamp'):
            ts = ts.timestamp()
        session.last_update_time = ts
        
        data = session.model_dump(mode='json', exclude_none=True)
        # Scrub large blobs to stay under 1MB limit
        data = scrub_blobs(data)
        # Stringify events to bypass Firestore's nested array limitation
        data["events"] = json.dumps(data.get("events", []))
        
        await self.db.collection(self.collection_name).document(session.id).set(data)
        return event

    async def update_session(self, *, user_id: str, session_id: str, app_name: str, state_update: Dict[str, Any]) -> None:
        doc_ref = self.db.collection(self.collection_name).document(session_id)
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            state = data.get("state", {})
            state.update(state_update)
            await doc_ref.update({"state": state})

    async def list_sessions(self, *, user_id: str, app_name: str) -> List[Session]:
        docs = self.db.collection(self.collection_name).where("user_id", "==", user_id).where("app_name", "==", app_name).stream()
        results = []
        async for doc in docs:
            data = doc.to_dict()
            events_data = data.get("events")
            if isinstance(events_data, str):
                try:
                    data["events"] = json.loads(events_data)
                except:
                    data["events"] = []
            # Rescue legacy invalid base64 strings
            data = rescue_blobs(data)
            results.append(Session.model_validate(data))
        return results

    async def list_sessions_for_user(self, *, user_id: str, app_name: str) -> List[Session]:
        return await self.list_sessions(user_id=user_id, app_name=app_name)

    async def delete_session(self, *, user_id: str, session_id: str, app_name: str) -> None:
        await self.db.collection(self.collection_name).document(session_id).delete()

# Initialize session service
try:
    session_service = FirestoreSessionService()
    logger.info("Using custom FirestoreSessionService for storage")
except Exception as e:
    logger.warning(f"Falling back to InMemorySessionService: {e}")
    session_service = InMemorySessionService()
    # Patch InMemorySessionService to support update_session to avoid crashes
    if not hasattr(session_service, "update_session"):
        async def update_session_mock(*, user_id, session_id, app_name, state_update):
            sess = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=app_name)
            if sess:
                sess.state.update(state_update)
        session_service.update_session = update_session_mock
    
    if not hasattr(session_service, "list_sessions_for_user"):
        async def list_sessions_for_user_mock(*, user_id, app_name):
            return await session_service.list_sessions(user_id=user_id, app_name=app_name)
        session_service.list_sessions_for_user = list_sessions_for_user_mock

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


# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UploadedFile(BaseModel):
    name: str
    mime_type: str
    data: str  # Base64 encoded data

class ResearchRequest(BaseModel):
    query: str
    mode: str = "quick"
    sessionId: str = None
    files: List[UploadedFile] = []

class FileItem(BaseModel):
    path: str
    type: str  # 'audio', 'video', 'presentation'
    name: str

class ResearchResponse(BaseModel):
    content: str
    files: List[FileItem]

from fastapi import Depends, Header

import firebase_admin
from firebase_admin import auth as firebase_auth

# Initialize Firebase Admin
# If running on GCP, it will automatically use the environment's project ID.
# On local, ensure GOOGLE_APPLICATION_CREDENTIALS points to a service account key or use default.
try:
    firebase_admin.get_app()
except ValueError:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VITE_FIREBASE_PROJECT_ID")
    if project_id:
        firebase_admin.initialize_app(options={'projectId': project_id})
    else:
        firebase_admin.initialize_app()

async def get_current_user(authorization: str = Header(None)):
    """
    Verifies the Firebase ID token sent from the frontend.
    """
    is_dev = os.getenv("ENV") == "development"
    
    if not authorization:
        if is_dev:
            logger.info("No auth header, using dev_user for local development")
            return "dev_user"
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Expect header in the form: "Bearer <token>"
        parts = authorization.strip().split(" ", 1)
        if len(parts) != 2 or not parts[1]:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            )
        scheme, token = parts[0], parts[1]
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization scheme. Expected 'Bearer'.",
            )
        # Verify the ID token using Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token.get("uid", "unknown_user")
    except HTTPException:
        # Re-raise HTTPExceptions unchanged
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        if is_dev:
            logger.warning("Token verification failed locally. Falling back to dev_user.")
            return "dev_user"
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

@app.post("/api/research", response_model=ResearchResponse)
async def research_endpoint(request: ResearchRequest, user_id: str = Depends(get_current_user)):
    logger.info(f"Received research request from {user_id}: {request.query} (mode: {request.mode})")
    try:
        # Depending on the mode, we might want to adjust the prompt or agent config,
        # but for now we pass the query to the root agent.
        # The deep-search agent is designed to route automatically.
        
        # Invoke the agent using the ADK Runner
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
            logger.warning(
                f"Error while checking for existing session {session_id} for user {user_id}: {e}",
                exc_info=True,
            )

        if not session_exists:
            try:
                logger.info(f"Initializing session: {session_id}")
                await session_service.create_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
            except Exception:
                logger.exception(f"Error initializing session: {session_id}")
                raise
        
        
        
        # Save the query as the title if this is a fresh session
        try:
            # Re-fetch or check state to see if title is needed
            curr = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
            if not curr.state or "title" not in curr.state:
                await session_service.update_session(
                    user_id=user_id, 
                    session_id=session_id, 
                    app_name=adk_app.name,
                    state_update={
                        "title": request.query[:50] + ("..." if len(request.query) > 50 else ""),
                        "mode": request.mode
                    }
                )
        except Exception:
            logger.exception(f"Error setting session title for session: {session_id}")

        # Construct content object
        parts = [types.Part(text=request.query)]
        for f in request.files:
            try:
                # Decode base64 to bytes
                file_bytes = base64.b64decode(f.data)
                parts.append(types.Part(inline_data=types.Blob(mime_type=f.mime_type, data=file_bytes)))
                logger.info(f"Added file to request: {f.name} ({f.mime_type})")
            except Exception as e:
                logger.error(f"Failed to process file {f.name}: {e}")
                
        content = types.Content(parts=parts)

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

@app.get("/api/threads")
async def get_user_threads(user_id: str = Depends(get_current_user)):
    """
    Fetches all research threads (sessions) for the current user.
    """
    try:
        threads = []

        # Prefer using the session_service abstraction if it provides a
        # way to list sessions for a user. This keeps the endpoint
        # decoupled from the underlying storage (Firestore, in‑memory, etc.).
        session_list_fn = getattr(session_service, "list_sessions_for_user", None)
        if callable(session_list_fn):
            sessions = await session_list_fn(user_id=user_id, app_name=adk_app.name)
            for s in sessions or []:
                # Support both dict-like and object-like session representations.
                if isinstance(s, dict):
                    raw_state = s.get("state") or {}
                    session_id = s.get("session_id") or s.get("id")
                    title = (
                        (raw_state.get("title") if isinstance(raw_state, dict) else None)
                        or s.get("title")
                        or "Untitled Research"
                    )
                else:
                    raw_state = getattr(s, "state", None) or {}
                    session_id = getattr(s, "session_id", None) or getattr(s, "id", None)
                    if isinstance(raw_state, dict):
                        title = raw_state.get("title") or getattr(s, "title", None) or "Untitled Research"
                    else:
                        title = getattr(raw_state, "title", None) or getattr(s, "title", None) or "Untitled Research"

                if not session_id:
                    continue

                threads.append(
                    {
                        "id": session_id,
                        "title": title,
                    }
                )

            return {"threads": threads}

        # Fallback: directly query Firestore if no abstraction is available.
        # NOTE: This implementation makes assumptions about the internal structure
        # of FirestoreSessionService:
        # - It assumes sessions are stored in a 'sessions' collection
        # - It assumes documents have a 'user_id' field for filtering
        # - It assumes session state is stored in a 'state' field with an optional 'title' subfield
        # If the actual ADK implementation uses different collection names or field structures,
        # this fallback may return empty or incorrect results.
        try:
            from google.cloud import firestore

            db = firestore.AsyncClient()

            # This assumes FirestoreSessionService uses a collection named 'sessions'
            # and stores user_id in the document.
            # Note: Actual ADK collection/field names might vary.
            sessions_ref = db.collection("sessions").where("user_id", "==", user_id)
            docs = await sessions_ref.stream()

            async for doc in docs:
                data = doc.to_dict()
                session_id = data.get("session_id")

                # Use the 'title' from state if available, otherwise fallback
                title = data.get("state", {}).get("title", "Untitled Research")

                threads.append(
                    {
                        "id": session_id,
                        "title": title,
                    }
                )

            return {"threads": threads}
        except Exception as firestore_error:
            logger.error(f"Error fetching threads from Firestore: {firestore_error}")
            return {"threads": []}
    except Exception as e:
        logger.error(f"Error fetching threads: {e}")
        # Fallback for InMemory (no persistence anyway)
        return {"threads": []}

@app.get("/api/session/{session_id}")
async def get_session_history(session_id: str, user_id: str = Depends(get_current_user)):
    try:
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        if not session:
            return {"messages": [], "mode": "quick"}
        
        history = []
        for event in session.events:
            text = ""
            # ADK Event data extraction
            content = getattr(event, "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    # Collect all text parts
                    text_parts = [getattr(p, "text", "") for p in parts if getattr(p, "text", "")]
                    text = "\n".join(text_parts)
            
            # Fallbacks for text
            if not text:
                text = getattr(event, "text", "") or getattr(event, "output", "") or ""
            
            if not text or not str(text).strip():
                continue
            
            # Role detection
            role = getattr(event, "role", None)
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
            
        # Return both messages and the saved mode
        return {
            "messages": history, 
            "mode": session.state.get("mode", "quick")
        }
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}", exc_info=True)
        return {"messages": [], "mode": "quick"}
    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        return {"messages": []}

# Mount the built frontend (Vite's default output is 'dist')
# Note: In the Dockerfile, we will build the React app and place it in the 'dist' folder
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent intercepting API routes
        if full_path.startswith("api") or full_path.startswith("static"):
            raise HTTPException(status_code=404)
        
        # Check if file exists in dist
        path = os.path.join("dist", full_path)
        if os.path.isfile(path):
            from fastapi.responses import FileResponse
            return FileResponse(path)
            
        # Fallback to index.html for SPA routing
        from fastapi.responses import FileResponse
        return FileResponse("dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
