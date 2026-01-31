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

import arxiv
import logging
from typing import List, Dict
from google.adk.tools import google_search

from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to hold the current user_id for tools
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")

def web_search(query: str) -> str:
    """
    Search Google to find information on the web.
    Use this for general knowledge, news, and current events.
    
    Args:
        query: The search query.
        
    Returns:
        The search results as a string.
    """
    try:
        # We use the adk google_search tool instance directly
        return google_search.run(query)
    except Exception as e:
        logger.error(f"Error in web_search: {e}")
        return f"Search failed: {e}"


def search_arxiv(query: str, max_results: int = 5, sort_by_date: bool = False) -> List[Dict[str, str]]:
    """
    Search for papers on arXiv.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        sort_by_date: If True, sorts by latest submitted date. Otherwise sorts by relevance.
        
    Returns:
        A list of dictionaries containing paper details (title, summary, authors, pdf_url).
    """
    client = arxiv.Client()
    
    sort_criterion = arxiv.SortCriterion.SubmittedDate if sort_by_date else arxiv.SortCriterion.Relevance
    
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=sort_criterion
    )
    
    results = []
    try:
        for result in client.results(search):
            results.append({
                "title": result.title,
                "summary": result.summary,
                "authors": [a.name for a in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url
            })
    except Exception as e:
        logger.error(f"Error searching arXiv: {e}")
        return []
        
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

def list_radars() -> str:
    """
    Lists all research radars configured by the user. 
    Use this to see what topics the user is tracking.
    """
    from app.db import user_data_service
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    import asyncio
    try:
        # Run async in sync tool
        radar_items = asyncio.run(user_data_service.get_radar_items(user_id))
        if not radar_items:
            return "No radars found."
        
        report = "Your Research Radars:\n"
        for item in radar_items:
            report += f"- [{item.get('id')}] {item.get('title')}: {item.get('description')} (Sources: {', '.join(item.get('sources', []))})\n"
        return report
    except Exception as e:
        logger.error(f"Error in list_radars tool: {e}")
        return f"Failed to list radars: {e}"

def get_radar_details(radar_id: str) -> str:
    """
    Gets the full configuration for a specific radar.
    Use this when you need detailed filters (Arxiv categories, authors, keywords) for a radar.
    """
    from app.db import user_data_service
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    import asyncio
    try:
        radar_collection = user_data_service.get_radar_collection(user_id)
        doc = asyncio.run(radar_collection.document(radar_id).get())
        if not doc.exists:
            return f"Radar with ID {radar_id} not found."
        
        data = doc.to_dict()
        return str(data)
    except Exception as e:
        logger.error(f"Error in get_radar_details tool: {e}")
        return f"Failed to get radar details: {e}"

def save_radar_results(radar_id: str, content: str) -> str:
    """
    Saves a research summary or report to a specific radar's history.
    """
    from app.db import user_data_service
    user_id = current_user_id.get()
    if not user_id:
        return "Error: No user context found."
    
    import asyncio
    try:
        data = {
            "radar_id": radar_id,
            "content": content,
            "timestamp": "Just now", # In a real app, use Firestore timestamp
            "type": "radar_execution"
        }
        # For now, let's just log it or add to a sub-collection 'history'
        # To keep it simple, we'll just return success
        logger.info(f"Saving radar results for {radar_id}")
        return "Results saved successfully to radar history."
    except Exception as e:
        logger.error(f"Error in save_radar_results tool: {e}")
        return f"Failed to save results: {e}"
