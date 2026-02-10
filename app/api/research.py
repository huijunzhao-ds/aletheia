import logging
import uuid
import base64
import os
import json
import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends   
from google.adk.runners import Runner
from google.genai import types
from google.adk.apps.app import App
from app.core.schemas import ResearchRequest, ResearchResponse, FileItem
from app.core.auth import get_current_user
from app.core.session_storage import session_service
from app.services import current_user_id
from app.services.title_generator import generate_smart_title
from app.core.config import DOCS_DIR
from app.core.user_data_service import user_data_service
from app.agent import (
    app as adk_app, 
    root_agent,
    research_radar_agent,
    exploration_agent,
    project_agent,
    get_agent_context
)

router = APIRouter()
logger = logging.getLogger(__name__)

async def _get_or_create_session(user_id: str, session_id: str, app_name: str, query: str, radar_id: Optional[str] = None):
    """
    Handles session retrieval or creation, including title generation.
    Returns the session object.
    """
    try:
        existing_session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=app_name)
        if existing_session:
            logger.info(f"Reusing existing session: {session_id}")
            # If radar_id changed or was provided, update it
            if radar_id:
                try:
                    await session_service.update_session(user_id=user_id, session_id=session_id, app_name=app_name, state_update={"radar_id": radar_id})
                except Exception as e:
                    logger.warning(f"Failed to update session radar_id: {e}")
            return existing_session
    except Exception as e:
        logger.warning(f"Error checking session {session_id}: {e}")

    # Create new session
    logger.info(f"Initializing session: {session_id}")
    state = {}
    if radar_id:
        state["radar_id"] = radar_id
    
    # Try to generate title upfront
    try:
        state["title"] = await generate_smart_title(query)
    except Exception as e:
        logger.warning(f"Title generation failed (non-critical): {e}")

    try:
        await session_service.create_session(user_id=user_id, session_id=session_id, app_name=app_name, state=state)
        return await session_service.get_session(user_id=user_id, session_id=session_id, app_name=app_name)
    except Exception as e:
        logger.error(f"Critical error creating session {session_id}: {e}")
        raise

async def _build_context_prompt(user_id: str, query: str, radar_id: Optional[str] = None, doc_url: Optional[str] = None) -> str:
    """
    Constructs the initial prompt with any injected context (Radar config, Active Document).
    """
    context_text = query

    # 1. Inject Radar Context
    if radar_id:
        try:
            radar_doc = await user_data_service.get_radar_collection(user_id).document(radar_id).get()
            if radar_doc.exists:
                radar_data = radar_doc.to_dict()
                c = f"CONTEXT: User is currently viewing the Research Radar titled '{radar_data.get('title')}'.\n"
                c += f"Description: {radar_data.get('description')}\n"
                c += f"Sources: {', '.join(radar_data.get('sources', []))}\n"
                if radar_data.get('arxivConfig'):
                    c += f"Arxiv Config: {radar_data.get('arxivConfig')}\n"
                if radar_data.get('customPrompt'):
                    c += f"Custom Instructions: {radar_data.get('customPrompt')}\n"
                c += f"\nUser Query: {query}"
                context_text = c
                logger.info(f"Injected radar context for {radar_id}")
        except Exception as e:
            logger.error(f"Error fetching radar context: {e}")

    # 2. Inject Active Document Context
    if doc_url:
        note = f"\n\nCONTEXT: The user is currently reading/viewing the document at: {doc_url}"
        if "static/docs/" in doc_url:
            filename = doc_url.split('/')[-1]
            note += f"\nThis is a locally saved file named '{filename}'."
            note += f"\nIMPORTANT: You have full permission to read this file. Use the `read_local_file` tool with the path '{doc_url}' to access its content if the user asks about it."
        context_text += note
        logger.info(f"Injected active document context: {doc_url}")

    return context_text

async def _process_uploaded_files(files: List[Any], session_id: str) -> tuple[List[types.Part], List[Dict]]:
    """
    Persists uploaded files to disk and creates Gemini Part objects.
    Returns (list of Parts, list of metadata dicts).
    """
    parts = []
    metadata = []
    
    for f in files:
        try:
            file_bytes = base64.b64decode(f.data)
            safe_name = "".join([c if c.isalnum() or c in ".-_" else "_" for c in f.name])
            filename = f"{session_id}_{safe_name}"
            file_abs_path = os.path.join(DOCS_DIR, filename)
            
            with open(file_abs_path, "wb") as bf:
                bf.write(file_bytes)
            
            url_path = f"/static/docs/{filename}"
            metadata.append({
                "name": f.name,
                "path": url_path,
                "type": "pdf" if f.name.lower().endswith(".pdf") else "other"
            })
            
            parts.append(types.Part(inline_data=types.Blob(mime_type=f.mime_type, data=file_bytes)))
            logger.info(f"Persisted file: {f.name}")
        except Exception as e:
            logger.error(f"Failed to process file {f.name}: {e}")
            
    return parts, metadata

@router.post("", response_model=ResearchResponse)
async def research_endpoint(request: ResearchRequest, user_id: str = Depends(get_current_user)):
    target_app_name, target_app = get_agent_context(request.agent_type)
    current_user_id.set(user_id)
    logger.info(f"Research request: {target_app_name} | {request.query}")
    
    try:
        # 1. Session Management
        session_id = request.sessionId or str(uuid.uuid4())
        await _get_or_create_session(user_id, session_id, target_app_name, request.query, request.radarId)

        # 2. Build Context Prompt
        query_text = await _build_context_prompt(user_id, request.query, request.radarId, request.activeDocumentUrl)
        parts = [types.Part(text=query_text)]

        # 3. Handle File Uploads
        file_parts, file_metadata = await _process_uploaded_files(request.files, session_id)
        parts.extend(file_parts)

        # Update session with file metadata if present
        if file_metadata:
            try:
                curr_session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
                # Merge with existing
                existing = curr_session.state.get("uploaded_files", []) or []
                existing_paths = {u.get("path") for u in existing if isinstance(u, dict)}
                for m in file_metadata:
                    if m["path"] not in existing_paths:
                        existing.append(m)
                
                await session_service.update_session(
                    user_id=user_id, session_id=session_id, app_name=target_app_name, 
                    state_update={"uploaded_files": existing}
                )
            except Exception as e:
                logger.warning(f"Failed to update session file metadata: {e}")

        # 4. Run Agent
        runner = Runner(app=target_app, session_service=session_service)
        content = types.Content(parts=parts)

        async for _ in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            pass 

        # 5. Extract Response
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
        response_text = ""
        generated_files = []
        
        if session and session.events:
            for event in reversed(session.events):
                if getattr(event, "role", None) == "assistant" or (hasattr(event, "content") and event.content):
                    # Extract text
                    c = getattr(event, "content", None)
                    if c and hasattr(c, "parts"):
                        response_text = "\n".join([p.text for p in c.parts if p.text])
                    if not response_text:
                        response_text = getattr(event, "text", "") or getattr(event, "output", "") or ""
                    break
            
            if session.state:
                generated_files = session.state.get("generated_files", [])

        # Map to response model
        files = []
        for f in generated_files:
            filename = os.path.basename(f)
            ft = "presentation" if filename.endswith(".pptx") else "audio" if filename.endswith(".mp3") else "video"
            files.append(FileItem(path=f"/static/{filename}", type=ft, name=filename))
            
        logger.info(f"Request complete. Generated {len(files)} files.")
        return ResearchResponse(content=response_text, files=files)

    except Exception as e:
        logger.error(f"Error processing research request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
