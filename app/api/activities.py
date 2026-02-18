from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any
from app.core.auth import get_current_user
from app.services.user_profiling import user_profiling_service

router = APIRouter()

@router.post("", response_model=Dict[str, str])
async def log_activity(
    activity: Dict[str, Any], 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Endpoint for frontend to log user activities.
    Body should be: {"type": "...", "details": {...}}
    """
    act_type = activity.get("type", "unknown")
    details = activity.get("details", {})
    
    background_tasks.add_task(
        user_profiling_service.log_activity, 
        user_id, 
        act_type, 
        details
    )
    
    return {"status": "queued"}
