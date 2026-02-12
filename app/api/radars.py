import datetime
import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.core.schemas import Radar, RadarCreate, RadarUpdate
from app.core.auth import get_current_user
from app.core.user_data_service import user_data_service
from app.services.scheduler import execute_radar_sync

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=Dict[str, str])
async def create_radar(radar: RadarCreate, user_id: str = Depends(get_current_user)):
    logger.info(f"Creating radar for user {user_id}: {radar.title}")
    try:
        if radar.frequency not in ["Hourly", "Daily", "Weekly", "Monthly"]:
            raise HTTPException(status_code=400, detail="Invalid frequency. Must be 'Hourly', 'Daily', 'Weekly', or 'Monthly'.")

        data = radar.model_dump()
        data["created_at"] = datetime.datetime.now(datetime.timezone.utc)
        data["lastUpdated"] = "Never"
        data["status"] = "active"
        
        # Add to Firestore
        update_time, doc_ref = await user_data_service.add_radar_item(user_id, data)
        return {"id": doc_ref.id, "message": "Radar created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating radar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_radars(user_id: str = Depends(get_current_user)):
    try:
        docs = user_data_service.get_radar_collection(user_id).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            # Ensure fields exist
            results.append(d)
        return results
    except Exception as e:
        logger.error(f"Error fetching radars: {e}")
        return []
        
@router.get("/{radar_id}")
async def get_radar(radar_id: str, user_id: str = Depends(get_current_user)):
    try:
        doc = await user_data_service.get_radar_collection(user_id).document(radar_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Radar not found")
        d = doc.to_dict()
        d["id"] = doc.id
        return d
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching radar {radar_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/briefing")
async def get_radar_briefing(radar_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    """
    Returns a briefing message for the Research Radar view.
    """
    try:
        if radar_id:
            radar_doc = await user_data_service.get_radar_collection(user_id).document(radar_id).get()
            if not radar_doc.exists:
                return {"summary": "Radar configuration not found for radar_id: {radar_id}"}
            
            data = radar_doc.to_dict()
            name = data.get('title', 'this radar')
            summary = data.get('latest_summary')
            last_updated = data.get('lastUpdated')
            last_viewed = data.get('lastViewed')

            # Track view immediately
            await user_data_service.track_radar_viewed(user_id, radar_id)

            # Scenario 1: No parse ever happened
            if not last_updated:
                return {
                    "scenario": "new",
                    "summary": f"Welcome to the **{name}** radar! I am ready to monitor this space for you. Would you like to start with an initial sweep to see what's currently trending?"
                }

            # Scenario 2: New parse that user hasn't reviewed
            is_new_parse = not last_viewed or last_updated > last_viewed
            if is_new_parse:
                return {
                    "scenario": "unviewed",
                    "summary": f"It's been a while since you last reviewed the updates for **{name}**. I've found some new developments since {last_viewed or 'you started'}:\n\n{summary}\n\nWhere would you like to start exploring?"
                }

            # Scenario 3: Pickup existing work
            return {
                "scenario": "resuming",
                "summary": f"Welcome back to **{name}**! We were previously analyzing the latest updates. Here is the last summary we discussed:\n\n{summary}\n\nLet's continue our research. What's on your mind?"
            }

        # Global briefing
        radars = await user_data_service.get_radar_items(user_id)
        if not radars:
            return {
                "summary": "Research Radar allows you to track real-time updates. Configure your first radar to begin monitoring specialized sources."
            }
        
        titles = [r.get('title') for r in radars]
        ## TODO: make the summary more personalized
        return {
            "summary": f"Welcome back! Your radars are actively monitoring **{', '.join(titles)}**. Which one would you like to dive into today?"
        }
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        return {"summary": "Ready to track your research updates."}

@router.post("/{radar_id}/sync")
async def sync_radar(radar_id: str, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    """
    Triggers a proactive sweep of the latest information for a specific radar.
    """
    logger.info(f"Sync requested for radar {radar_id} by user {user_id}")
    background_tasks.add_task(execute_radar_sync, user_id, radar_id)
    return {"message": "Sync started in background."}

@router.put("/{radar_id}", response_model=Dict[str, str])
async def update_radar(radar_id: str, radar: RadarCreate, user_id: str = Depends(get_current_user)):
    logger.info(f"Updating radar {radar_id} for user {user_id}")
    try:
        # Validate frequency
        if radar.frequency not in ["Hourly", "Daily", "Weekly", "Monthly"]:
            raise HTTPException(status_code=400, detail="Invalid frequency. Must be 'Hourly', 'Daily', 'Weekly', or 'Monthly'.")

        data = radar.model_dump()
        data["lastUpdated"] = "Just updated"
        
        await user_data_service.update_radar_item(user_id, radar_id, data)
        return {"message": "Radar updated successfully"}
    except Exception as e:
        logger.error(f"Error updating radar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{radar_id}", response_model=Dict[str, str])
async def delete_radar(radar_id: str, user_id: str = Depends(get_current_user)):
    logger.info(f"Deleting radar {radar_id} for user {user_id}")
    try:
        await user_data_service.delete_radar_item(user_id, radar_id)
        return {"message": "Radar deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting radar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{radar_id}/read")
async def mark_radar_read(radar_id: str, user_id: str = Depends(get_current_user)):
    """Marks the radar as read/viewed by updating the lastViewed timestamp."""
    try:
        await user_data_service.track_radar_viewed(user_id, radar_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error marking radar {radar_id} read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{radar_id}/status")
async def update_radar_status(radar_id: str, status: str, user_id: str = Depends(get_current_user)):
    if status not in ["active", "paused"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    await user_data_service.update_radar_status(user_id, radar_id, status)
    return {"status": "success"}

@router.get("/{radar_id}/items")
async def get_radar_items_endpoint(radar_id: str, user_id: str = Depends(get_current_user)):
    items = await user_data_service.get_radar_captured_items(user_id, radar_id)
    logger.info(f"Fetched {len(items)} items for radar {radar_id} and user {user_id}")
    return items

@router.delete("/{radar_id}/items/{item_id}")
async def delete_radar_captured_item_endpoint(radar_id: str, item_id: str, user_id: str = Depends(get_current_user)):
    await user_data_service.delete_radar_captured_item(user_id, radar_id, item_id)
    return {"status": "success"}
