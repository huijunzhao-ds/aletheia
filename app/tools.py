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

logger = logging.getLogger(__name__)

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


def search_arxiv(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for papers on arXiv.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        
    Returns:
        A list of dictionaries containing paper details (title, summary, authors, pdf_url).
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
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
