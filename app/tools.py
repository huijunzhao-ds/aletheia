# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import arxiv
import logging
from typing import List, Dict, Optional
import datetime
from google.adk.tools import google_search

from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to hold the current user_id for tools
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")
# Context variable to hold the current radar_id for tools during sync
current_radar_id: ContextVar[str] = ContextVar("current_radar_id", default="")

def web_search(query: str) -> str:
    """
    Search Google to find information on the web.
    Use this for general knowledge, news, and current events.
    
    Args:
        query: The search query.
        
    Returns:
        The search results as a string.
    """
    import httpx
    import urllib.parse
    
    try:
        # We use a direct HTTP lookup to avoid complex internal ADK context mismatches
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                # Basic snippet extraction from the HTML results
                import re
                html = response.text
                
                # Remove scripts and styles to save tokens
                html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
                html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL)
                
                # Remove HTML tags to get raw text
                text = re.sub(r'<[^>]+>', ' ', html)
                
                # Normalize whitespace
                text = ' '.join(text.split())
                
                # We return the top portion of the CLEANED text
                return text
            else:
                return f"Search returned status code {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error in web_search: {e}")
        return f"Search failed: {e}"


def search_arxiv(query: str, max_results: int = 5, sort_by_date: bool = False, published_after: Optional[datetime.datetime] = None) -> List[Dict[str, str]]:
    """
    Search for papers on arXiv.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        sort_by_date: If True, sorts by latest submitted date. Otherwise sorts by relevance.
        published_after: Optional datetime. If provided, excludes papers published before this time.
        
    Returns:
        A list of dictionaries containing paper details (title, summary, authors, pdf_url).
    """
    # If published_after is set, we want ALL papers in that window, so we uncap max_results
    # The loop will terminate based on the date check or server-side filter.
    search_max_results = float('inf') if published_after else max_results

    # Configure client with retries and optimized page size
    # If max_results is distinct, scale page size. If infinite/all, use 100.
    if search_max_results and search_max_results != float('inf'):
         page_size = min(search_max_results * 4, 100) if search_max_results > 0 else 100
    else:
         page_size = 100

    client = arxiv.Client(
        page_size=page_size,
        delay_seconds=3.0,
        num_retries=3
    )
    
    # Construct the final query with server-side date filtering if applicable
    final_query = query.strip() if query else ""
    
    if published_after:
        # ArXiv API format: YYYYMMDDHHMM
        # We construct a range from published_after to a far future date
        start_date = published_after.strftime("%Y%m%d%H%M")
        # Use a reasonable future year to cover "now"
        end_date = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y%m%d%H%M")
        
        date_filter = f"submittedDate:[{start_date} TO {end_date}]"
        
        if final_query:
            # Group original query to ensure boolean logic works as expected (Query AND Date)
            final_query = f"({final_query}) AND {date_filter}"
        else:
            final_query = date_filter

    if not final_query:
        logger.warning("Arxiv search called with empty query and no date filter.")
        return []

    sort_criterion = arxiv.SortCriterion.SubmittedDate if sort_by_date else arxiv.SortCriterion.Relevance
    
    # arxiv library documentation says: max_results (int): ... default is 10.
    # Current implementation of python-arxiv (v2.x) uses a generator. 
    # Passing float('inf') might crash it if it expects int. 
    # Let's use a standard explicit check.
    _limit = search_max_results if (search_max_results and search_max_results != float('inf')) else None

    search = arxiv.Search(
        query=final_query,
        max_results=_limit,
        sort_by=sort_criterion
    )
    
    results = []
    try:
        # Execute search
        # Note: We trust the server-side date filter, but we also double-check 
        # because the API can sometimes be fuzzy or return 'updated' dates that differ.
        for result in client.results(search):
            
            # Additional client-side safety check for date
            if published_after:
                res_date = result.published
                if not res_date.tzinfo:
                    res_date = res_date.replace(tzinfo=datetime.timezone.utc)
                
                check_date = published_after
                if not check_date.tzinfo:
                    check_date = check_date.replace(tzinfo=datetime.timezone.utc)

                if res_date < check_date:
                    # If we find a paper older than the cutoff
                    if sort_by_date:
                        # Optimization: if sorted by date, all subsequent are older
                        break
                    # Otherwise (Relevance sort), just skip this one
                    continue

            results.append({
                "title": result.title,
                "summary": result.summary,
                "authors": [a.name for a in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url
            })
            
    except Exception as e:
        logger.error(f"Error searching arXiv: {e}")
        # Return whatever we found so far instead of empty list if possible, or just empty
        return results
        
    return results

def generate_audio_summary(text: str) -> str:
    """
    Generates an audio file reading the provided text.
    Use this to create a podcast-style summary or explanation for the user.
    
    Args:
        text: The text content to be spoken.
        
    Returns:
        The path to the generated audio file.
    """
    from app.multimodal import generate_audio_file
    return generate_audio_file(text)

def generate_presentation_file(title: str, slides: List[Dict[str, str]]) -> str:
    """
    Generates a PowerPoint presentation file.
    
    Args:
        title: The title of the presentation.
        slides: A list of dictionaries, where each dict has a 'title' string and a 'content' string.
                Example: [{"title": "Intro", "content": "Hello World"}]
                
    Returns:
        The path to the generated .pptx file.
    """
    from app.multimodal import generate_presentation
    return generate_presentation(title, slides)

def generate_video_lecture_file(title: str, slides: List[Dict[str, str]]) -> str:
    """
    Generates an MP4 video lecture.
    
    Args:
        title: The title of the lecture.
        slides: A list of dictionaries, where each dict has a 'title' string and a 'content' string.
                Content is spoken in the video and shown on the slide.
                Example: [{"title": "Concept A", "content": "Explanation of A..."}]
                
    Returns:
        The path to the generated .mp4 file.
    """
    from app.multimodal import generate_video_lecture
    return generate_video_lecture(title, slides)

def scrape_website(url: str) -> str:
    """
    Fetches and extracts text content from a given URL.
    Use this to collect articles, blog posts, or documentation.
    
    Args:
        url: The URL to scrape.
        
    Returns:
        The text content of the website.
    """
    import httpx
    import re
    
    try:
        # User defined headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            # Simple text extraction (stripping HTML tags)
            # In a real app, use BeautifulSoup
            html = response.text
            # Remove scripts and styles
            html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL)
            # Remove tags
            text = re.sub(r'<[^>]+>', ' ', html)
            # Normalize whitespace
            text = ' '.join(text.split())
            
            return text[:20000] # Limit content size
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return f"Failed to read content from {url}: {e}"

# --- Database Tools for Research Radar Agent ---

async def list_radars() -> str:
    """
    Lists all research radars configured by the user. 
    Use this to see what topics the user is tracking.
    """
    from app.db import user_data_service
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
    from app.db import user_data_service
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
    from app.db import user_data_service
    from app.multimodal import generate_audio_file
    import datetime
    
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
    from app.db import user_data_service
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

def read_local_file(file_path: str) -> str:
    """
    Reads the text content of a local file saved in the system (e.g., from 'static/docs/').
    Supports PDF and text/markdown files.
    If the file is missing locally but exists in GCS backup, it will be restored.
    
    Args:
        file_path: The name or path of the file to read (e.g., 'static/docs/paper.pdf' or just 'paper.pdf').
        
    Returns:
        The text content of the file.
    """
    try:
        # Sanitize and resolve path
        # Check if full path or just filename
        if "static/docs/" in file_path:
            target_path = file_path.lstrip("/") # Remove leading slash if present
        else:
            target_path = os.path.join("static/docs", os.path.basename(file_path))
            
        # LAZY RESTORE FROM GCS if missing
        if not os.path.exists(target_path):
            try:
                # Try to restore from GCS (Cloud Run ephemeral storage fix)
                from app.storage import get_storage_client, BUCKET_NAME
                client = get_storage_client()
                if client:
                    bucket = client.bucket(BUCKET_NAME)
                    filename = os.path.basename(target_path)
                    blob_name = f"docs/{filename}"
                    blob = bucket.blob(blob_name)
                    
                    if blob.exists():
                        logger.info(f"Restoring missing file from GCS: {blob_name}")
                        # Ensure dir exists
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        blob.download_to_filename(target_path)
                    else:
                        logger.warning(f"File not found locally or in GCS: {blob_name}")
            except Exception as e:
                logger.warning(f"Failed to restore from GCS: {e}")

        if not os.path.exists(target_path):
            return f"Error: File not found at {target_path} (and restore failed)"
            
        # Security check: ensure path is within static/docs
        abs_target = os.path.abspath(target_path)
        abs_root = os.path.abspath("static/docs")
        if not abs_target.startswith(abs_root):
            return "Error: Access denied. Can only read files in static/docs/."
            
        file_ext = os.path.splitext(target_path)[1].lower()
        
        if file_ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(target_path)
                text = ""
                # Limit to first 20 pages to avoid context overflow for massive docs
                max_pages = 20
                for i, page in enumerate(reader.pages):
                    if i >= max_pages:
                        text += "\n[...Document Truncated...]"
                        break
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "Error: pypdf library not installed. Cannot read PDF."
            except Exception as e:
                return f"Error reading PDF: {e}"
        else:
            # Assume text/markdown
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Error reading local file {file_path}: {e}")
        return f"Failed to read file: {e}"
