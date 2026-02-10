from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging
from app.core.auth import get_current_user
from app.core.user_data_service import user_data_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/save")
async def save_to_project(item: dict, user_id: str = Depends(get_current_user)):
    try:
        # We might want to remove 'id' if successful to create a NEW id for the project item? 
        # Or keep it as a reference? Usually standard to clean 'id' before adding new doc.
        item_data = item.copy()
        if "id" in item_data:
            del item_data["id"]
        
        await user_data_service.add_project_item(user_id, item_data)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving to project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
