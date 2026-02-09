import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import get_current_user
from app.core.session_storage import session_service
from app.agent import app as adk_app, get_agent_context

router = APIRouter()
logger = logging.getLogger(__name__)

@router.delete("/{session_id}")
async def delete_thread(session_id: str, agent_type: Optional[str] = 'exploration', user_id: str = Depends(get_current_user)):
    target_app_name, _ = get_agent_context(agent_type)
    try:
        await session_service.delete_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
        return {"status": "success", "message": f"Thread {session_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting thread {session_id}: {e}")
        # Try finding in default app just in case
        try:
            await session_service.delete_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_user_threads(radar_id: Optional[str] = None, agent_type: Optional[str] = 'exploration', user_id: str = Depends(get_current_user)):
    target_app_name, _ = get_agent_context(agent_type)
    try:
        threads = []
        session_list_fn = getattr(session_service, "list_sessions_for_user", None)

        if callable(session_list_fn):
            sessions = await session_list_fn(user_id=user_id, app_name=target_app_name, radar_id=radar_id)
            
            # Merge legacy sessions (from default 'Aletheia' app scope) to prevent history loss
            if target_app_name != adk_app.name:
                try:
                    legacy_sessions = await session_list_fn(user_id=user_id, app_name=adk_app.name, radar_id=radar_id)
                    # Deduplicate based on session ID
                    if sessions is None:
                        sessions = []
                    existing_ids = set()
                    for s in sessions:
                        sid = getattr(s, "session_id", None) or getattr(s, "id", None)
                        if isinstance(s, dict):
                            sid = s.get("session_id") or s.get("id")
                        if sid:
                            existing_ids.add(sid)
                            
                    for ls in legacy_sessions or []:
                        ls_id = getattr(ls, "session_id", None) or getattr(ls, "id", None)
                        if isinstance(ls, dict):
                            ls_id = ls.get("session_id") or ls.get("id")
                        
                        if ls_id and ls_id not in existing_ids:
                            sessions.append(ls)
                except Exception as ex:
                    logger.warning(f"Failed to fetch legacy threads: {ex}")

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
                    # Filter out internal/system sessions
                    # 1. Check ID pattern (sync_*)
                    if str(session_id).startswith("sync_"):
                        continue
                    # 2. Check Title pattern (System sweeping/thinking)
                    if str(title).startswith("System sweeping") or str(title).startswith("System thinking"):
                        continue

                    threads.append({
                        "id": session_id, 
                        "title": title,
                        "radarId": raw_state.get("radar_id")
                    })
            return {"threads": threads}
        return {"threads": []}
    except Exception as e:
        logger.error(f"Error fetching threads: {e}")
        return {"threads": []}
