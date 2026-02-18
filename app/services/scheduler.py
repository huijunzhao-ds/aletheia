
import logging
import datetime
import json
import uuid
import os
import random
import asyncio
from time import time
from google import genai
from google.genai import types
from app.services import current_user_id, current_radar_id, search_arxiv
from app.core.session_storage import session_service
from app.core.user_data_service import user_data_service
from app.services.user_profiling import user_profiling_service


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
        
        # 4a. Process Papers & Save to DB (Fully Parallel)
        is_audio_podcast = radar_data.get('outputMedia') == 'Audio Podcast'
        
        # Helper to generate audio in thread
        def _generate_audio_sync(text):
            import re
            from app.services import generate_audio_summary
            # Strip markdown and excessive newlines
            clean_text = re.sub(r'\*\*|__', '', text) 
            clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)
            clean_text = re.sub(r'#{1,6}\s?', '', clean_text)
            clean_text = re.sub(r'\n+', ' ', clean_text).strip()
            return generate_audio_summary(clean_text)

        loop = asyncio.get_running_loop()

        async def _process_and_save_paper(paper):
            try:
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

                
                # 1. Generate Recommendation Reason (User Profiling)
                recommendation_reason = ""
                try:
                    reason = await user_profiling_service.generate_recommendation_reason(user_id, item_data)
                    if reason:
                        recommendation_reason = reason
                        item_data["recommendation_reason"] = reason
                        # also append to summary for visibility
                        original_summary = item_data.get("summary", "")
                        item_data["summary"] = f"**Why relevant to you:** {reason}\n\n{original_summary}"
                except Exception as e:
                    logger.warning(f"Failed to generate recommendation reason: {e}")

                # 2. Generate individual audio if requested
                if is_audio_podcast:
                    try:
                        # Construct text for TTS (Title + Reason + Summary)
                        tts_text = f"Title: {paper.get('title')}. "
                        
                        if recommendation_reason:
                             tts_text += f"Reason for recommendation: {recommendation_reason}. "
                        
                        tts_text += f"Summary: {paper.get('summary')}"
                        
                        # Truncate to reasonable length for TTS
                        if len(tts_text) > 2000:
                            # Try validation or auto-summary first if text is huge
                            try:
                                if user_profiling_service.client:
                                    logger.info(f"Summarizing long text for TTS ({len(tts_text)} chars)")
                                    summary_prompt = f"""Summarize the following research paper abstract for an audio brief. 
                                    Keep the Title and 'Reason for Recommendation' intact if possible.
                                    Target length: ~150 words.
                                    
                                    TEXT:
                                    {tts_text}
                                    """
                                    resp = await user_profiling_service.client.aio.models.generate_content(
                                        model="gemini-2.5-flash", 
                                        contents=summary_prompt,
                                        config=types.GenerateContentConfig(temperature=0.5)
                                    )
                                    tts_text = resp.text
                                else:
                                     tts_text = tts_text[:2000] + "..."
                            except Exception as sum_err:
                                logger.warning(f"TTS summarization failed, falling back to truncate: {sum_err}")
                                tts_text = tts_text[:2000] + "..."
                        
                        audio_path = await loop.run_in_executor(None, _generate_audio_sync, tts_text)
                        
                        if not audio_path.startswith("/"):
                            audio_path = "/" + audio_path
                        
                        item_data["asset_type"] = "audio"
                        item_data["asset_url"] = audio_path
                        logger.info(f"Generated audio for paper: {paper.get('title')[:30]}")
                    except Exception as e:
                        logger.error(f"Failed to generate audio for paper {paper.get('title')}: {e}")

                # Save to DB
                await user_data_service.add_radar_captured_item(user_id, radar_id, item_data)
                return True
            except Exception as e:
                logger.error(f"Failed to process paper {paper.get('title')}: {e}")
                return False

        # Execute all tasks concurrently
        tasks = [_process_and_save_paper(p) for p in real_papers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        save_count = sum(1 for r in results if r is True)

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

# --- Proactive Scheduling ---

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def check_all_radars():
    """
    Periodically checks all active radars across all users.
    Triggers execute_radar_sync if the update interval has passed.
    """
    logger.info("Running scheduled radar check...")
    try:
        all_user_ids = await user_data_service.get_all_users()
        tasks_to_run = []
        
        # 1. Collect all radars that need updating
        for user_id in all_user_ids:
            try:
                radars = await user_data_service.get_radar_items(user_id)
                for radar in radars:
                    if radar.get('status') == 'paused':
                        continue
                    
                    freq = radar.get('frequency', 'Hourly')
                    last_updated_str = radar.get('lastUpdated')
                    radar_id = radar.get('id')
                    
                    should_run = False
                    now = datetime.datetime.now(datetime.timezone.utc)
                    
                    if not last_updated_str or last_updated_str in ["Never", "Just updated"]:
                        should_run = last_updated_str == "Never"
                    else:
                        try:
                            last_updated = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
                            delta = now - last_updated
                            
                            if freq == 'Hourly' and delta > datetime.timedelta(hours=1): should_run = True
                            elif freq == 'Daily' and delta > datetime.timedelta(days=1): should_run = True
                            elif freq == 'Weekly' and delta > datetime.timedelta(days=7): should_run = True
                            elif freq == 'Monthly' and delta > datetime.timedelta(days=30): should_run = True
                        except Exception as e:
                            logger.warning(f"Error parsing date for radar {radar_id}: {e}")
                            should_run = True 

                    if should_run:
                        tasks_to_run.append((user_id, radar_id, freq))
            except Exception as ue:
                logger.error(f"Error checking radars for user {user_id}: {ue}")

        # 2. Execute sequentially to avoid rate limits
        if tasks_to_run:
            logger.info(f"Found {len(tasks_to_run)} radars to sync. executing sequentially...")
            # Shuffle to avoid same-user bias every run
            random.shuffle(tasks_to_run)
            
            for uid, rid, freq in tasks_to_run:
                try:
                    logger.info(f"Sequential Sync: Starting radar {rid} ({freq})")
                    await execute_radar_sync(uid, rid)
                    # Force a sleep between radars to satisfy ArXiv policy (and general load)
                    # Using 5 seconds to be safe
                    await asyncio.sleep(5) 
                except Exception as e:
                     logger.error(f"Error syncing radar {rid}: {e}")
        else:
            logger.info("No radars due for sync.")
            
    except Exception as e:
        logger.error(f"Scheduled check failed: {e}")

def start_scheduler():
    """Starts the background scheduler."""
    if not scheduler.running:
        # Check every 15 minutes
        scheduler.add_job(check_all_radars, 'interval', minutes=15)
        scheduler.start()
        logger.info("Proactive Radar Scheduler started (interval: 15m).")
