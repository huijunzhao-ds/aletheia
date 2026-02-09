import logging
import os
import json
import re
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import get_current_user
from app.core.session_storage import session_service
from app.agent import app as adk_app, get_agent_context

router = APIRouter()
logger = logging.getLogger(__name__)

async def _resolve_session(user_id: str, session_id: str, app_name: str) -> Optional[Any]:
    """Retrieves session with fallback to default app context."""
    try:
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=app_name)
        if session:
            return session
            
        # Fallback to default app
        try:
             return await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        except:
             return None
    except Exception as e:
        logger.warning(f"Error resolving session {session_id}: {e}")
        return None

def _extract_text_from_event(event: Any) -> str:
    """Extracts and sanitizes text from a session event."""
    text = ""
    content = getattr(event, "content", None)
    
    if content:
        parts = getattr(content, "parts", None)
        if parts:
            text_parts = []
            for p in parts:
                p_text = getattr(p, "text", "")
                p_text_str = str(p_text or "")
                # Filter out scrubbed file placeholder
                if p_text_str and "[External file data not preserved in history]" not in p_text_str:
                    text_parts.append(p_text_str)
            text = "\n".join(text_parts)
    
    if not text:
        raw_text = getattr(event, "text", "") or getattr(event, "output", "") or ""
        if "[External file data not preserved in history]" not in str(raw_text):
            text = raw_text
            
    return text

def _determine_message_role(event: Any, text: str) -> str:
    """Determines the role (user, assistant, tool, system) of the event."""
    role = None
    
    # 1. Check direct 'author' attribute
    author = getattr(event, "author", None)
    if author:
        author_str = str(author).lower()
        if "user" in author_str: return "user"
        if any(m in author_str for m in ("assistant", "model", "aletheia")): return "assistant"
        if "system" in author_str: return "system"
        if "tool" in author_str: return "tool"

    # 2. Check 'role' attribute
    if not role:
        role = getattr(event, "role", None)
        if isinstance(role, str): role = role.lower()
    
    # 3. Check content role
    content = getattr(event, "content", None)
    if not role and content:
        role = getattr(content, "role", None)
        if isinstance(role, str): role = role.lower()

    # 4. Final heuristic fallback
    if role not in ("user", "assistant", "system", "tool"):
        event_type = str(getattr(event, "type", "") or getattr(event, "event_type", "")).lower()
        if any(k in event_type for k in ("user", "input", "request")):
            role = "user"
        elif "thought" in text.lower() or "thinking" in event_type or "tool" in event_type:
            # Check for user-facing tool outputs
            is_user_facing = False
            tool_name = getattr(event, "tool_name", "") or getattr(event, "function_name", "") or ""
            
            if any(t in tool_name for t in ["generate_audio_summary", "generate_presentation_file", "generate_video_lecture_file"]):
                is_user_facing = True
            
            if text.strip().endswith(".mp3") or text.strip().endswith(".pptx") or text.strip().endswith(".mp4"):
                if "/static/" in text or "http" in text:
                    is_user_facing = True

            return "assistant" if is_user_facing else "tool"
        else:
            role = "unknown"
            
    return role

def _sanitize_user_text(text: str) -> str:
    """Removes system directives and context injection from user messages."""
    if "SYSTEM DIRECTIVE:" in text:
        return "" 
    elif "CONTEXT:" in text and "User Query:" in text:
        match = re.search(r"User Query:\s*(.*)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return text

def _match_files_to_message(role: str, event: Any, unassigned_uploads: list, unassigned_generated: list, text: str) -> list:
    """Matches uploaded or generated files to the current message."""
    msg_files = []
    content = getattr(event, "content", None)
    
    # 1. Match Uploaded Files (User role)
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
    if role == "assistant" and unassigned_generated:
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
    return msg_files

def _collect_session_docs(gen_files: list, uploaded_files: list) -> list:
    """Collects all session-wide documents."""
    all_docs = []
    
    # Generated files
    for f in gen_files:
        path = f if isinstance(f, str) else f.get("path")
        name = os.path.basename(path) if isinstance(f, str) else f.get("name", os.path.basename(path))
        if path and (path.lower().endswith(".pdf") or (isinstance(f, dict) and f.get("type") == "pdf")):
            all_docs.append({
                "name": name,
                "url": path if path.startswith("/") or "://" in path else f"/{path}"
            })
    
    # Uploaded files
    for f in uploaded_files:
        if isinstance(f, dict) and f.get("type") == "pdf":
            path = f.get("path")
            all_docs.append({
                "name": f.get("name"),
                "url": path if path.startswith("/") or "://" in path else f"/{path}"
            })
            
    return all_docs

@router.get("/{session_id}")
async def get_session_history(session_id: str, agent_type: Optional[str] = 'exploration', user_id: str = Depends(get_current_user)):
    target_app_name, _ = get_agent_context(agent_type)
    
    session = await _resolve_session(user_id, session_id, target_app_name)
    if not session:
        return {"messages": []}
    
    # Prepare pools
    history = []
    gen_files = session.state.get("generated_files", []) or []
    uploaded_files = session.state.get("uploaded_files", []) or []
    unassigned_uploads = list(uploaded_files)
    unassigned_generated = list(gen_files)
    
    logger.info(f"Loading history for session {session_id}. State has {len(uploaded_files)} uploads and {len(gen_files)} generated files.")
    
    for event in session.events:
        text = _extract_text_from_event(event)
        role = _determine_message_role(event, text)
        if role not in ("user", "assistant"):
            continue   
        msg_files = _match_files_to_message(role, event, unassigned_uploads, unassigned_generated, text)
        if role == "user":
            text = _sanitize_user_text(text)
        if not text.strip() and not msg_files:
            continue
        history.append({
            "id": str(event.id),
            "role": role,
            "content": text,
            "timestamp": event.timestamp,
            "files": msg_files
        })
        
    return {
        "messages": history,
        "documents": _collect_session_docs(gen_files, uploaded_files)
    }
