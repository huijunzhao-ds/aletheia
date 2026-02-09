import logging
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import get_current_user
from app.core.user_data_service import user_data_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/init")
async def init_user_data(user_id: str = Depends(get_current_user)):
    """
    Initializes the user's data structures in Firestore (Radar, Exploration, Projects).
    """
    try:
        await user_data_service.initialize_user_collections(user_id)
        return {"status": "success", "message": f"User {user_id} initialized."}
    except Exception as e:
        logger.error(f"Error initializing user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize user data")
