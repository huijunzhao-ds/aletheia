import logging
import os
import uuid
import datetime
import httpx
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from app.core.auth import get_current_user
from app.core.user_data_service import user_data_service
from app.core.session_storage import upload_to_gcs
from app.core.config import STATIC_DIR

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/save")
async def save_to_exploration(item: dict, user_id: str = Depends(get_current_user)):
    try:
        # Check if we have a URL to download
        source_url = item.get("url") or item.get("pdf_url")
        if source_url:
            try:
                logger.info(f"Downloading content from {source_url}...")
                async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                    resp = await client.get(source_url)
                    if resp.status_code == 200:
                        # Check content-type header to confirm PDF
                        ct = resp.headers.get("content-type", "").lower()
                        ext = "pdf" if "application/pdf" in ct or source_url.lower().endswith(".pdf") else "html"
                        
                        # Generate filename
                        safe_title = "".join([c if c.isalnum() else "_" for c in item.get("title", "untitled")])[:50]
                        filename = f"expl_{uuid.uuid4().hex[:8]}_{safe_title}.{ext}"
                        local_path = os.path.join(STATIC_DIR, "docs", filename)
                        
                        # 1. Attempt GCS Upload (Persistence)
                        try:
                            gcs_uri = upload_to_gcs(resp.content, f"docs/{filename}", content_type=ct if ct else "application/pdf")
                            if gcs_uri:
                                item["gcsUri"] = gcs_uri
                                logger.info(f"Persisted to GCS: {gcs_uri}")
                        except Exception as gcs_err:
                            logger.error(f"GCS Upload failed (continuing with local only): {gcs_err}")

                        # 2. Save locally (Performance/Cache)
                        with open(local_path, "wb") as f:
                            f.write(resp.content)
                            
                        # Update item with local asset path
                        item["localAssetPath"] = f"/static/docs/{filename}"
                        item["localAssetType"] = ext
                        logger.info(f"Saved downloaded content to {local_path}")
            except Exception as e:
                logger.error(f"Failed to download exploration content: {e}")
                # We continue saving the metadata even if download fails

        await user_data_service.add_exploration_item(user_id, item)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving to exploration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_exploration_item(
    title: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    try:
        content = await file.read()
        
        # Determine extension
        filename = file.filename or "untitled"
        ext = "pdf" if filename.lower().endswith(".pdf") else "dat"
        # Extract meaningful name if possible
        
        # Generate safe filename
        safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
        unique_filename = f"expl_{uuid.uuid4().hex[:8]}_{safe_title}.{ext}"
        local_path = os.path.join(STATIC_DIR, "docs", unique_filename)
        
        with open(local_path, "wb") as f:
            f.write(content)
            
        # Create item
        item = {
            "id": str(uuid.uuid4()),
            "title": title,
            "url": f"/static/docs/{unique_filename}",
            "localAssetPath": f"/static/docs/{unique_filename}",
            "localAssetType": ext,
            "summary": "Uploaded file",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        await user_data_service.add_exploration_item(user_id, item)
        return {"status": "success", "item": item}
    except Exception as e:
        logger.error(f"Error uploading item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_exploration_items(user_id: str = Depends(get_current_user)):
    try:
        items = await user_data_service.get_exploration_items(user_id)
        return {"items": items}
    except Exception as e:
        logger.error(f"Error fetching exploration items: {e}")
        return {"items": []}

@router.put("/{item_id}/archive")
async def archive_exploration_item(item_id: str, archived: bool, user_id: str = Depends(get_current_user)):
    try:
        await user_data_service.update_exploration_item(user_id, item_id, {"isArchived": archived})
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error archiving item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{item_id}")
async def delete_exploration_item(item_id: str, user_id: str = Depends(get_current_user)):
    try:
        await user_data_service.delete_exploration_item(user_id, item_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting exploration item: {e}")
        raise HTTPException(status_code=500, detail=str(e))
