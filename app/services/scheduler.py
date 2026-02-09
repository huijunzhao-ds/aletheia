
import logging
import datetime
import json
import uuid
from google.adk.runners import Runner
from google.adk.apps.app import App
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
        # We want any of the keywords to appear in EITHER title OR abstract
        kw_terms = []
        for k in keywords:
            clean_k = k.strip()
            if clean_k:
                kw_terms.append(f"ti:{clean_k}")
                kw_terms.append(f"abs:{clean_k}")
        
        if kw_terms:
            logic = arxiv_config.get('keywordLogic', 'OR').upper()
            join_op = " AND " if logic == "AND" else " OR "
            kw_part = join_op.join(kw_terms)
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

async def _filter_duplicate_papers(user_id: str, radar_id: str, papers: list) -> list:
    """Filters out papers that have already been captured for this radar."""
    if not papers:
        return []

    # Fetch existing captured keys to filter out duplicates
    existing_keys = await user_data_service.get_all_radar_captured_keys(user_id, radar_id)
    existing_urls = {k.get("source_url") for k in existing_keys if k.get("source_url")}
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

def _construct_briefing_prompt(radar_data: dict, radar_id: str, papers: list) -> str:
    """Constructs the system directive prompt for the agent."""
    query = f"SYSTEM DIRECTIVE: You MUST perform a research briefing for the following Radar.\n"
    query += f"TARGET_TITLE: **{radar_data.get('title')}**\n"
    query += f"TARGET_RADAR_ID: **{radar_id}**\n\n"
    
    if papers:
        query += f"I have found {len(papers)} new papers from Arxiv:\n"
        query += json.dumps(papers, indent=2)
        query += f"\n\nCRITICAL INSTRUCTION: You MUST call the `save_radar_item` tool for EACH paper found. Use the exact ID '{radar_id}' for the `unique_topic_token` argument. Do NOT claim the ID is None. The ID is provided right here: {radar_id}.\n"
        query += "\nFor each call, provide the specific paper title as `item_title`, a detailed academic digest (3-4 paragraphs) as `item_summary`, the list of authors as `authors`, and the PDF URL as `source_url`."
        query += "\n\nFINAL OUTPUT REQUIREMENT: "
        query += "After saving all items, your final text response MUST be a concise but informative 'Briefing Update' for the user. "
        query += "It should state: 'I found X new papers.' followed by a bulleted list of the papers found with a 1-sentence topic summary for each. "
        query += "Do not just say 'I have saved the items'. Give the user the high-level news."
    else:
        query += "No new Arxiv papers were found in the immediate sweep, but please check other sources for any significant updates and synthesize a report."
        
    return query

async def _run_briefing_session(user_id: str, radar_id: str, radar_title: str, query: str) -> str:
    """Runs the agent session to process the briefing prompt."""
    job_session_id = f"sync_{radar_id}_{uuid.uuid4().hex[:8]}"
    target_sync_app_name = "aletheia_radar"
    from app.agent import root_agent

    
    # Add descriptive title for data auditing
    sync_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sync_title = f"System sweeping for {sync_date}"
    
    await session_service.create_session(
        user_id=user_id, 
        session_id=job_session_id, 
        app_name=target_sync_app_name, 
        state={
            "radar_id": radar_id,
            "title": sync_title 
        }
    )
    
    scoped_sync_app = App(root_agent=root_agent, name=target_sync_app_name)
    runner = Runner(app=scoped_sync_app, session_service=session_service)
    content = types.Content(parts=[types.Part(text=query)])
    
    response_text = ""
    async for _ in runner.run_async(user_id=user_id, session_id=job_session_id, new_message=content):
        pass

    # Fetch the final session to get the full assistant response
    final_session = await session_service.get_session(user_id=user_id, session_id=job_session_id, app_name=target_sync_app_name)
    if final_session and final_session.events:
        for event in reversed(final_session.events):
            if getattr(event, "role", None) == "assistant":
                content_attr = getattr(event, "content", None)
                if content_attr and hasattr(content_attr, "parts") and content_attr.parts:
                    response_text = "\n".join([str(p.text or "") for p in content_attr.parts if hasattr(p, "text") and p.text])
                    break
                    
    return response_text

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
        real_papers = search_arxiv(query=search_query, max_results=max_search, sort_by_date=True, published_after=cutoff_time)
        
        # 2. Deduplication
        real_papers = await _filter_duplicate_papers(user_id, radar_id, real_papers)

        if real_papers:
            # 3. Semantic Ranking
            real_papers = await rank_papers_with_llm(real_papers, radar_data.get('title'), radar_data.get('description', ''), limit=15)

            logger.info(f"Found {len(real_papers)} new unique papers for radar {radar_id}")
            for i, paper in enumerate(real_papers, 1):
                logger.info(f"  Paper {i}: {paper.get('title', 'N/A')} by {', '.join(paper.get('authors', [])[:3])}")
        else:
            logger.info(f"No new unique papers found for radar {radar_id}")

        # 4. Construct Agent Prompt
        query = _construct_briefing_prompt(radar_data, radar_id, real_papers)
            
        # 5. Run Agent Session
        response_text = await _run_briefing_session(user_id, radar_id, radar_data.get('title'), query)
        
        if not response_text:
            response_text = f"The research sweep for {radar_data.get('title')} is complete."

        await user_data_service.save_radar_summary(user_id, radar_id, response_text, captured_inc=0)
        logger.info(f"Proactive sync completed for radar {radar_id}")

    except Exception as e:
        logger.error(f"Error in background sync for {radar_id}: {e}", exc_info=True)

# Helper function for semantic ranking
async def rank_papers_with_llm(papers: list, radar_title: str, radar_description: str, limit: int = 15) -> list:
    """
    Uses the LLM to rank papers by semantic relevance to the radar description.
    This helps filter out unrelated papers that matched broad keywords.
    """
    if not papers:
        return []

    # If few papers, just return them
    if len(papers) <= limit:
         return papers

    logger.info(f"Ranking {len(papers)} papers for radar '{radar_title}'...")
    
    prompt = f"TASK: You are a research relevance expert. Select the TOP {limit} most relevant papers for the topic below based on their title and abstract.\n\n"
    prompt += f"TOPIC: {radar_title}\n"
    prompt += f"DESCRIPTION: {radar_description}\n\n"
    prompt += "Evaluate each paper below:\n"
    
    # We truncate abstract to save tokens but keep enough for relevance
    # Provide index for easy selection
    for i, p in enumerate(papers):
        # Clean title
        title = str(p.get('title', '')).replace('\n', ' ').strip()
        summary = str(p.get('summary', '')).replace('\n', ' ').strip()[:300]
        prompt += f"[{i}] {title}\nAbstract: {summary}...\n\n"
        
    prompt += f"OUTPUT INSTRUCTION: Return ONLY a JSON list of integers representing the indices of the top {limit} papers, sorted by relevance (most relevant first). Example: [4, 1, 12]"

    # Use a temporary session for ranking
    # We use a unique ID to avoid collision
    temp_session_id = f"rank_{uuid.uuid4().hex[:8]}"
    from app.agent import root_agent
    rank_app = App(root_agent=root_agent, name="aletheia_ranker")
    
    try:
        # Create session
        await session_service.create_session(
            user_id="system_ranker", 
            session_id=temp_session_id, 
            app_name="aletheia_ranker",
            state={}
        )

        runner = Runner(app=rank_app, session_service=session_service)
        
        # Run inference
        # We manually construct a user message to trigger the agent
        # Note: root_agent might be chatty. We hope it follows instructions.
        content = types.Content(parts=[types.Part(text=prompt)])
        
        async for _ in runner.run_async(user_id="system_ranker", session_id=temp_session_id, new_message=content):
            pass
            
        # Get response
        final_session = await session_service.get_session(user_id="system_ranker", session_id=temp_session_id, app_name="aletheia_ranker")
        response_text = ""
        
        if final_session and final_session.events:
             for event in reversed(final_session.events):
                if getattr(event, "role", None) == "assistant":
                    content_attr = getattr(event, "content", None)
                    if content_attr and hasattr(content_attr, "parts") and content_attr.parts:
                        response_text = "\n".join([str(p.text or "") for p in content_attr.parts if getattr(p, "text", None)])
                        break
        
        # Parse output
        selected_indices = []
        if response_text:
            import re
            # Try to find JSON list
            match = re.search(r"\[.*?\]", response_text, re.DOTALL)
            if match:
                try:
                    selected_indices = json.loads(match.group(0))
                except:
                    logger.warning(f"Failed to parse ranking JSON: {response_text[:100]}...")
            else:
                 logger.warning(f"No JSON found in ranking response: {response_text[:100]}...")

        # Filter papers
        ranked_papers = []
        if isinstance(selected_indices, list):
            for idx in selected_indices:
                if isinstance(idx, int) and 0 <= idx < len(papers):
                    ranked_papers.append(papers[idx])
        
        # If parsing failed or empty, fallback to original order up to limit
        if not ranked_papers:
            logger.warning("Ranking returned no valid papers, falling back to date sort.")
            return papers[:limit]
            
        logger.info(f"Ranking complete. Selected {len(ranked_papers)} papers.")
        return ranked_papers

    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        # Cleanup
        try:
             await session_service.delete_session(user_id="system_ranker", session_id=temp_session_id, app_name="aletheia_ranker")
        except:
             pass
        return papers[:limit]
