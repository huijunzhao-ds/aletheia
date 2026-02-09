import logging
import os
import datetime
from typing import List
from app.core.user_data_service import user_data_service
from .context import current_user_id, current_radar_id
from .multimodal import generate_audio_file

logger = logging.getLogger(__name__)

async def list_radars() -> str:
    """
    Lists all research radars configured by the user. 
    Use this to see what topics the user is tracking.
    """
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    try:
        # Await async DB call directly
        radar_items = await user_data_service.get_radar_items(user_id)
        if not radar_items:
            return "No radars found."
        
        report = "Your Research Radars:\n"
        for item in radar_items:
            rid = item.get('id')
            title = item.get('title')
            desc = item.get('description')
            report += f"--- RADAR START ---\n"
            report += f"ID: {rid}\n"
            report += f"TITLE: {title}\n"
            report += f"DESCRIPTION: {desc}\n"
            report += f"--- RADAR END ---\n"
        return report
    except Exception as e:
        logger.error(f"Error in list_radars tool: {e}")
        return f"Failed to list radars: {e}"

async def get_radar_details(radar_id: str) -> str:
    """
    Gets the full configuration for a specific radar.
    Use this when you need detailed filters (Arxiv categories, authors, keywords) for a radar.
    """
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    try:
        radar_collection = user_data_service.get_radar_collection(user_id)
        doc = await radar_collection.document(radar_id).get()
        
        if not doc.exists:
            # Try fuzzy lookup by title
            all_radars = await user_data_service.get_radar_items(user_id)
            for r in all_radars:
                if r.get('title', '').lower() == radar_id.lower():
                    # Found it! Switch to the real ID and re-fetch doc
                    real_id = r['id']
                    doc = await radar_collection.document(real_id).get()
                    break
            
            if not doc.exists:
                return f"Radar with ID or Title '{radar_id}' not found. Please use list_radars to find the correct ID."
        
        data = doc.to_dict()
        data["id"] = doc.id
        return str(data)
    except Exception as e:
        logger.error(f"Error in get_radar_details tool: {e}")
        return f"Failed to get radar details: {e}"

async def save_radar_item(unique_topic_token: str, item_title: str, item_summary: str, authors: List[str] = None, source_url: str = None) -> str:
    """
    Saves a single research paper or finding to a specific radar. 
    
    Args:
        unique_topic_token: The internal ID of the research radar (e.g. 'abc-123').
        item_title: The title of the paper.
        item_summary: The summary text.
        authors: Optional list of author names for the paper.
        source_url: Optional URL to the original source (PDF or webpage).
    """
    radar_id = unique_topic_token
    
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    # If radar_id is not provided or is None, try to get it from context
    if not radar_id or radar_id == "None" or radar_id.lower() == "none":
        context_radar_id = current_radar_id.get()
        if context_radar_id:
            radar_id = context_radar_id
            logger.info(f"Using radar_id from context: {radar_id}")
        else:
            return "Error: No radar_id provided and no radar context found. Please specify the unique_topic_token."
    
    try:
        # Fuzzy lookup: if radar_id doesn't look like an ID or wasn't found, try finding by title
        radar_collection = user_data_service.get_radar_collection(user_id)
        radar_doc = await radar_collection.document(radar_id).get()
        
        target_radar_id = radar_id
        if not radar_doc.exists:
            logger.info(f"Radar ID {radar_id} not found, searching by title...")
            all_radars = await user_data_service.get_radar_items(user_id)
            found_by_title = None
            for r in all_radars:
                if r.get('title', '').lower() == radar_id.lower():
                    found_by_title = r
                    break
            
            if found_by_title:
                target_radar_id = found_by_title['id']
                radar_doc = await radar_collection.document(target_radar_id).get()
                logger.info(f"Found radar match: '{radar_id}' -> ID {target_radar_id}")
            else:
                return f"Error: Radar '{radar_id}' not found. Please use list_radars to find the correct ID."
            
        radar_data = radar_doc.to_dict()
        output_media = radar_data.get("outputMedia", "Text Digest")
        radar_id = target_radar_id 
        
        # Generate the asset path based on outputMedia
        asset_url = None
        asset_type = "markdown" # default
        
        # Ensure docs directory exists
        os.makedirs("static/docs", exist_ok=True)
        
        if output_media == "Audio Podcast":
            try:
                # Generate a natural language script for the audio
                audio_path = generate_audio_file(f"Summary of {item_title}. {item_summary}")
                asset_url = f"/{audio_path}"
                asset_type = "audio"
            except Exception as e:
                logger.error(f"Failed to generate audio for {item_title}: {e}")
        else:
            # Store as a .md file
            try:
                import uuid
                md_filename = f"{uuid.uuid4()}.md"
                md_path = f"static/docs/{md_filename}"
                with open(md_path, "w") as f:
                    f.write(f"# {item_title}\n\n{item_summary}")
                asset_url = f"/{md_path}"
                asset_type = "markdown"
            except Exception as e:
                logger.error(f"Failed to save markdown file: {e}")
        
        # Save as a captured item
        captured_data = {
            "title": item_title,
            "summary": item_summary,
            "authors": authors if authors else [],
            "parent": radar_id,
            "asset_url": asset_url,
            "asset_type": asset_type,
            "url": source_url,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        
        await user_data_service.add_radar_captured_item(user_id, radar_id, captured_data)
        
        # Update radar unread count based on 1 item
        await user_data_service.save_radar_summary(user_id, radar_id, item_summary[:500], captured_inc=1)
        
        return f"Successfully saved research item: {item_title}"
    except Exception as e:
        logger.error(f"Error in save_radar_item tool: {e}")
        return f"Failed to save result: {e}"

async def list_exploration_items() -> str:
    """
    Lists the items (articles, papers) saved in the user's Exploration / To Review list.
    Returns the title, summary (brief), and original URL or file path for each item.
    Use this to understand what documents the user has available for deep reading.
    """
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    try:
        items = await user_data_service.get_exploration_items(user_id)
        if not items:
            return "No items found in 'To Review' list."
            
        summary_list = []
        for item in items:
            title = item.get('title', 'Untitled')
            url = item.get('url') or item.get('pdf_url') or item.get('web_url') or "No URL"
            local_path = item.get('localAssetPath', "Not downloaded")
            desc = (item.get('summary') or '')[:100] + "..."
            summary_list.append(f"- Title: {title}\n  URL: {url}\n  Local Path: {local_path}\n  Snippet: {desc}\n")
            
        return "Found the following items in 'To Review' list:\n" + "\n".join(summary_list)
    except Exception as e:
        logger.error(f"Error listing exploration items: {e}")
        return f"Failed to list items: {e}"
