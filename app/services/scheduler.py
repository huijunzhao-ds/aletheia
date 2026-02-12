
import logging
import datetime
import json
import uuid
import os
import asyncio
from time import time
from google import genai
from google.genai import types
from app.services import current_user_id, current_radar_id, search_arxiv
from app.core.session_storage import session_service
from app.core.user_data_service import user_data_service

logger = logging.getLogger(__name__)

def _build_arxiv_query(radar_data: dict) -> str:
    """Helper to construct the Arxiv search query from radar configuration."""
    arxiv_config = radar_data.get('arxivConfig') or {}
    terms = []
    
    # 1. Categories
    categories = arxiv_config.get('categories')
    if isinstance(categories, list):
        cat_part = " OR ".join([f"cat:{c}" for c in categories])
        if cat_part:
            terms.append(f"({cat_part})")
    
    # 2. Keywords
    keywords = arxiv_config.get('keywords')
    if isinstance(keywords, list):
        kw_groups = [f"(ti:{k.strip()} OR abs:{k.strip()})" for k in keywords if k.strip()]
        if kw_groups:
            logic = arxiv_config.get('keywordLogic', 'OR').upper()
            join_op = " AND " if logic == "AND" else " OR "
            kw_part = join_op.join(kw_groups)
            terms.append(f"({kw_part})")
            
    if terms:
        return " AND ".join(terms)
    
    return radar_data.get('title', '')

async def _calculate_time_window(radar_data: dict, radar_id: str) -> tuple[datetime.datetime, int]:
    """Determines the cutoff time and max search results based on frequency and last update."""
    frequency = radar_data.get('frequency', 'Hourly')
    cutoff_time = None
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Check for system log of last successful sweep (lastUpdated)
    last_updated_str = radar_data.get('lastUpdated')
    parsed_last_updated = None
    
    if last_updated_str and last_updated_str not in ["Never", "Just updated"]:
        try:
            # Format from save_radar_summary is "%Y-%m-%d %H:%M"
            parsed = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M")
            parsed_last_updated = parsed.replace(tzinfo=datetime.timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to parse lastUpdated '{last_updated_str}' for radar {radar_id}: {e}")

    if parsed_last_updated:
        cutoff_time = parsed_last_updated
        max_search = 1000 # Use a large limit, tool will fetch all since cutoff
        logger.info(f"Using last successful sweep time as cutoff: {cutoff_time}")
    else:
        # Initial sweep or fallback based on frequency
        if frequency == 'Hourly':
            cutoff_time = now - datetime.timedelta(hours=2)
            max_search = 20
        elif frequency == 'Daily':
            cutoff_time = now - datetime.timedelta(days=2)
            max_search = 50
        elif frequency == 'Weekly':
            cutoff_time = now - datetime.timedelta(days=8)
            max_search = 100
        elif frequency == 'Monthly':
            cutoff_time = now - datetime.timedelta(days=32)
            max_search = 200
        else:
            # Default fallback
            cutoff_time = now - datetime.timedelta(days=2)
            max_search = 30
            
    return cutoff_time, max_search

async def _filter_duplicate_papers(user_id: str, radar_id: str, papers: list, since: datetime.datetime = None) -> list:
    """Filters out papers that have already been captured for this radar."""
    if not papers:
        return []

    # Fetch existing captured keys to filter out duplicates
    existing_keys = await user_data_service.get_all_radar_captured_keys(user_id, radar_id, since=since)
    existing_urls = {k.get("url") for k in existing_keys if k.get("url")}
    existing_titles = {k.get("title", "").lower().strip() for k in existing_keys if k.get("title")}
    
    unique_papers = []
    for paper in papers:
        p_url = paper.get("pdf_url") or paper.get("link")
        p_title = paper.get("title", "").lower().strip()
        
        # Check URL match
        if p_url and p_url in existing_urls:
            continue
        
        # Check Title match (fuzzy or exact)
        if p_title and p_title in existing_titles:
            continue
            
        unique_papers.append(paper)
        
    return unique_papers

async def _generate_briefing_with_llm(radar_title: str, papers: list) -> str:
    """Generates a concise briefing update using a direct LLM call."""
    if not papers:
        return f"No new papers found for {radar_title} in this sweep."

    prompt = f"""You are a research assistant.
    Generate a concise 'Briefing Update' for the user about these new papers found for the Radar '{radar_title}'.
    
    REQUIREMENTS:
    - Start with 'I found X new papers.'
    - Provide a bulleted list of the top 5 papers.
    - For each, write a 1-sentence takeaway.
    - Keep it high-level and news-worthy.
    
    PAPERS:
    """
    for i, p in enumerate(papers[:10]): # Limit context
        prompt += f"- {p.get('title')}: {p.get('summary')[:200]}...\n"

    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key: 
            return "New papers found (LLM summary unavailable)."
            
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as e:
        logger.error(f"Briefing generation failed: {e}")
        return f"Found {len(papers)} new papers. Please check the list."

async def execute_radar_sync(user_id: str, radar_id: str):
    current_user_id.set(user_id)
    current_radar_id.set(radar_id)
    
    try:
        radar_doc = await user_data_service.get_radar_collection(user_id).document(radar_id).get()
        if not radar_doc.exists:
            logger.error(f"Sync failed: Radar {radar_id} not found")
            return
        
        radar_data = radar_doc.to_dict()
        search_query = _build_arxiv_query(radar_data)

        # 1. Determine Time Window
        cutoff_time, max_search = await _calculate_time_window(radar_data, radar_id)
        logger.info(f"Running real Arxiv search for radar {radar_id} with query: {search_query} since {cutoff_time}")
        real_papers = search_arxiv(query=search_query, max_results=max_search, published_after=cutoff_time)
        
        # 2. Deduplication
        real_papers = await _filter_duplicate_papers(user_id, radar_id, real_papers, since=cutoff_time)

        if not real_papers:
            logger.info(f"No new unique papers found for radar {radar_id}")
            # Optimization: Skip everything if no papers
            await user_data_service.save_radar_summary(user_id, radar_id, "No new papers found in the latest sweep.", captured_inc=0)
            return

        # 3. Semantic Ranking  
        real_papers = await rank_papers_with_llm(real_papers, radar_data.get('title'), radar_data.get('description', ''), limit=15)

        logger.info(f"Found {len(real_papers)} new unique papers for radar {radar_id}")
        
        # 4. Parallel Process: Save Items & Generate Briefing
        
        # 4a. Save to DB directly (Parallel)
        save_tasks = []
        for paper in real_papers:
            # Map paper dict to firestore schema
            item_data = {
                "title": paper.get("title"),
                "url": paper.get("pdf_url") or paper.get("link"),
                "summary": paper.get("summary"), # Use abstract as summary
                "authors": paper.get("authors", []),
                "published": paper.get("published"),
                "source": "arxiv",
                "added_at": datetime.datetime.now(datetime.timezone.utc),
                "radar_id": radar_id
            }
            # Add task
            save_tasks.append(user_data_service.add_radar_captured_item(user_id, radar_id, item_data))

        if save_tasks:
            
            # Run all save tasks concurrently
            results = await asyncio.gather(*save_tasks, return_exceptions=True)
            # Count successes
            save_count = sum(1 for r in results if not isinstance(r, Exception))
            # Log errors
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.error(f"Failed to save paper {real_papers[i].get('title')}: {r}")

        # 4b. Generate Briefing (LLM)
        start_time = time()
        response_text = await _generate_briefing_with_llm(radar_data.get('title'), real_papers)
        end_time = time()
        logger.info(f"Briefing generated in {end_time - start_time} seconds")
        
        await user_data_service.save_radar_summary(user_id, radar_id, response_text, captured_inc=save_count)
        logger.info(f"Proactive sync completed for radar {radar_id}")

    except Exception as e:
        logger.error(f"Error in background sync for {radar_id}: {e}", exc_info=True)

# Helper function for semantic ranking
async def rank_papers_with_llm(papers: list, radar_title: str, radar_description: str, limit: int = 15) -> list:
    """
    Uses the LLM to rank papers by semantic relevance to the radar description.
    This helps filter out unrelated papers that matched broad keywords.
    """
    # If few papers, just return them
    if len(papers) <= limit:
         return papers

    logger.info(f"Ranking {len(papers)} papers for radar '{radar_title}'...")
    
    prompt = f"""You are a research relevance expert. 
    Select the TOP {limit} most relevant papers for the topic below based on their title and abstract.
    TOPIC: {radar_title}
    DESCRIPTION: {radar_description}
    
    PAPERS:
    """
    for i, p in enumerate(papers):
        title = str(p.get('title', '')).replace('\n', ' ').strip()
        summary = str(p.get('summary', '')).replace('\n', ' ').strip()
        prompt += f"[{i}] {title}\nAbstract: {summary}...\n\n"

    prompt += f"""
    OUTPUT INSTRUCTION: 
    Return a JSON list of integers representing the indices of the top {limit} papers, 
    sorted by relevance (most relevant first). 
    Example: [4, 1, 12]
    """

    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
             logger.warning("No API Key found for ranking. Returning unranked list.")
             return papers[:limit]

        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", 
                temperature=0.1
            )
        )
        selected_indices = json.loads(response.text)
        # Filter and Return
        ranked_papers = []
        if isinstance(selected_indices, list):
            for idx in selected_indices:
                if isinstance(idx, int) and 0 <= idx < len(papers):
                    ranked_papers.append(papers[idx])
        
        if not ranked_papers:
            logger.warning("Ranking returned empty list, falling back to date sort.")
            return papers[:limit]
            
        logger.info(f"Ranking complete. Selected {len(ranked_papers)} papers.")
        return ranked_papers

    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        return papers[:limit]
