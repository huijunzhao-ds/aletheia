import os
from typing import Dict, Optional
import logging
import uuid
import base64
import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure the current directory is in sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ADK and Application Imports
from google.adk.runners import Runner
from google.genai import types
from app.agent import (
    app as adk_app, 
    root_agent,
    research_radar_agent,
    exploration_agent,
    project_agent,
    search_agent
)
from google.adk.apps.app import App
from app.schemas import ResearchRequest, ResearchResponse, FileItem
from app.auth import get_current_user
from app.sessions import get_session_service
from app.tools import current_user_id
from app.title_gen import generate_smart_title

# Initialize session service
session_service = get_session_service()

app = FastAPI()

# Static files setup with absolute paths for cloud safety
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOCS_DIR = os.path.join(STATIC_DIR, "docs")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ... (runner logic) ...

# Global Scheduler for proactive features
scheduler = AsyncIOScheduler()

async def scheduled_radar_sync_all():
    """
    Proactive feature: Iterates through all users and all active radars 
    to perform a research sync at 0:00 every day.
    """
    from app.db import user_data_service
    
    logger.info("Starting global proactive radar sync...")
    user_ids = await user_data_service.get_all_users()
    
    today = datetime.datetime.now(datetime.timezone.utc)
    is_monday = today.weekday() == 0
    is_first_of_month = today.day == 1
    
    sync_count = 0
    for uid in user_ids:
        try:
            radars = await user_data_service.get_radar_items(uid)
            for radar in radars:
                if radar.get('status') != 'active':
                    continue
                
                freq = radar.get('frequency', 'Daily')
                
                # Check last updated to prevent duplicate runs on the same day/session
                last_updated_str = radar.get('lastUpdated', '')
                already_run_today = False
                try:
                    # Format is "%Y-%m-%d %H:%M" in UTC
                    if len(last_updated_str) >= 10:
                        last_date_str = last_updated_str[:10]
                        today_str = today.strftime("%Y-%m-%d")
                        if last_date_str == today_str:
                                already_run_today = True
                except Exception as e:
                    logger.debug(f"Failed to parse lastUpdated '{last_updated_str}' for radar {radar.get('id')}: {e}")

                should_run = False
                
                if freq == 'Daily':
                    if not already_run_today:
                        should_run = True
                elif freq == 'Weekly':
                    if is_monday and not already_run_today:
                        should_run = True
                elif freq == 'Monthly':
                    if is_first_of_month and not already_run_today:
                        should_run = True
                    
                if should_run:
                    logger.info(f"Proactively syncing radar {radar.get('id')} for user {uid}")
                    # We run this as a background task to not block the scheduler loop
                    await execute_radar_sync(uid, radar.get('id'))
                    sync_count += 1
        except Exception as e:
            logger.error(f"Error checking radars for user {uid}: {e}")
            
    logger.info(f"Global proactive sync completed. Synced {sync_count} radars.")

@app.on_event("startup")
async def startup_event():
    # Schedule the proactive sync at 0:00 every day
    # Note: Use hour=0, minute=0 for production. Set to shorter for testing if needed.
    scheduler.add_job(
        scheduled_radar_sync_all, 
        CronTrigger(hour=0, minute=0),
        id="daily_radar_sync",
        replace_existing=True
    )
    scheduler.start()
    
    # Run a sync check immediately on startup to catch up if missed
    import asyncio
    asyncio.create_task(scheduled_radar_sync_all())
    
    logger.info("APScheduler started: Daily proactive sync scheduled at 0:00 and initial check triggered.")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/research", response_model=ResearchResponse)
async def research_endpoint(request: ResearchRequest, user_id: str = Depends(get_current_user)):
    # Determine app_name based on agent_type
    target_app_name = f"aletheia_{request.agent_type}" if request.agent_type else adk_app.name

    # Set context for tools
    current_user_id.set(user_id)
    
    logger.info(f"Received research request from {user_id} for {target_app_name}: {request.query}")
    try:
        # Select the appropriate root agent based on context (Direct Routing)
        # This bypasses the generic router for specific contexts to ensure correct tool availability
        target_agent = root_agent
        if request.agent_type == 'radar':
            target_agent = research_radar_agent
        elif request.agent_type == 'exploration':
            target_agent = exploration_agent
        elif request.agent_type == 'projects':
            target_agent = project_agent
        
        # Create a scoped app instance for this request to match the target_app_name
        scoped_app = App(root_agent=target_agent, name=target_app_name)
        runner = Runner(app=scoped_app, session_service=session_service)
        session_id = request.sessionId or str(uuid.uuid4())
        
        # Check if session exists, if not create it
        session_exists = False
        try:
            existing_session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
            if existing_session:
                session_exists = True
                logger.info(f"Reusing existing session: {session_id}")
        except Exception as e:
            logger.warning(f"Error while checking for existing session {session_id}: {e}")

        if not session_exists:
            try:
                logger.info(f"Initializing session: {session_id}")
                state = {}
                if request.radarId:
                    state["radar_id"] = request.radarId
                await session_service.create_session(user_id=user_id, session_id=session_id, app_name=target_app_name, state=state)
            except Exception:
                logger.exception(f"Error initializing session: {session_id}")
                raise
        elif request.radarId:
            # Tag existing session if radarId is provided
            await session_service.update_session(user_id=user_id, session_id=session_id, app_name=target_app_name, state_update={"radar_id": request.radarId})
        
        # Save the query as the title if this is a fresh session
        try:
            curr = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
            if not curr.state or "title" not in curr.state:
                # Generate a smart title
                session_title = await generate_smart_title(request.query)
                
                await session_service.update_session(
                    user_id=user_id, 
                    session_id=session_id, 
                    app_name=target_app_name,
                    state_update={
                        "title": session_title
                    }
                )
        except Exception:
            logger.exception(f"Error setting session title for session: {session_id}")

        # Construct content object and persist files for history
        query_text = request.query
        
        # If radarId is provided, fetch radar config and prepend as context
        if request.radarId:
            from app.db import user_data_service
            try:
                radar_doc = await user_data_service.get_radar_collection(user_id).document(request.radarId).get()
                if radar_doc.exists:
                    radar_data = radar_doc.to_dict()
                    context = f"CONTEXT: User is currently viewing the Research Radar titled '{radar_data.get('title')}'.\n"
                    context += f"Description: {radar_data.get('description')}\n"
                    context += f"Sources: {', '.join(radar_data.get('sources', []))}\n"
                    if radar_data.get('arxivConfig'):
                        context += f"Arxiv Config: {radar_data.get('arxivConfig')}\n"
                    if radar_data.get('customPrompt'):
                        context += f"Custom Instructions: {radar_data.get('customPrompt')}\n"
                    context += f"\nUser Query: {request.query}"
                    query_text = context
                    logger.info(f"Injected radar context for {request.radarId}")
            except Exception as e:
                logger.error(f"Error fetching radar context: {e}")

        # If activeDocumentUrl is present (Exploration or Radar Chat), provide context
        if request.activeDocumentUrl:
            context_note = f"\n\nCONTEXT: The user is currently reading/viewing the document at: {request.activeDocumentUrl}"
            # Helper logic: if it's a local file, we might want to hint the agent to look for it, 
            # though usually the URL is enough if it matches a 'list_exploration_items' entry.
            if "static/docs/" in request.activeDocumentUrl:
                filename = request.activeDocumentUrl.split('/')[-1]
                context_note += f"\nThis is a locally saved file named '{filename}'."
                context_note += f"\nIMPORTANT: You have full permission to read this file. Use the `read_local_file` tool with the path '{request.activeDocumentUrl}' to access its content if the user asks about it."
                context_note += f"\nDO NOT REFUSE to read this file. It is safe and part of the user's research."
            
            query_text += context_note
            logger.info(f"Injected active document context: {request.activeDocumentUrl}")

        parts = [types.Part(text=query_text)]
        uploaded_doc_metadata = []
        
        for f in request.files:
            try:
                file_bytes = base64.b64decode(f.data)
                
                # Persist to static/docs/ with absolute path for cloud reliability
                safe_name = "".join([c if c.isalnum() or c in ".-_" else "_" for c in f.name])
                filename = f"{session_id}_{safe_name}"
                file_abs_path = os.path.join(DOCS_DIR, filename)
                
                with open(file_abs_path, "wb") as bf:
                    bf.write(file_bytes)
                
                if os.path.exists(file_abs_path):
                    logger.info(f"Successfully persisted file to disk: {file_abs_path}")
                else:
                    logger.error(f"Failed to find file on disk after write attempt: {file_abs_path}")
                
                url_path = f"/static/docs/{filename}"
                uploaded_doc_metadata.append({
                    "name": f.name,
                    "path": url_path,
                    "type": "pdf" if f.name.lower().endswith(".pdf") else "other"
                })
                
                parts.append(types.Part(inline_data=types.Blob(mime_type=f.mime_type, data=file_bytes)))
                logger.info(f"Added and persisted file: {f.name} ({f.mime_type})")
            except Exception as e:
                logger.error(f"Failed to process/persist file {f.name}: {e}")
                
        # Update session state with persisted file metadata
        if uploaded_doc_metadata:
            try:
                curr_session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
                existing_uploaded = curr_session.state.get("uploaded_files", [])
                # Deduplicate by path
                existing_paths = {uf.get("path") for uf in existing_uploaded if isinstance(uf, dict)}
                for doc in uploaded_doc_metadata:
                    if doc["path"] not in existing_paths:
                        existing_uploaded.append(doc)
                
                await session_service.update_session(
                    user_id=user_id,
                    session_id=session_id,
                    app_name=target_app_name,
                    state_update={"uploaded_files": existing_uploaded}
                )
            except Exception as e:
                logger.error(f"Failed to update session with uploaded file metadata: {e}")

        content = types.Content(parts=parts)

        # Execute runner
        async for _ in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            pass # We just consume the events to let the agent complete

        # Retrieve the updated session to get the final response
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
        
        response_text = ""
        generated_files = []
        
        if session and session.events:
            # The last event from the assistant is usually the final response
            # We look for the most recent message with a role or content
            last_message_event = None
            for event in reversed(session.events):
                if getattr(event, "role", None) == "assistant" or (hasattr(event, "content") and event.content):
                    last_message_event = event
                    break
            
            if last_message_event:
                # Extract text using the same logic as get_session_history
                content_attr = getattr(last_message_event, "content", None)
                if content_attr and hasattr(content_attr, "parts") and content_attr.parts:
                    response_text = "\n".join([getattr(p, "text", "") for p in content_attr.parts if getattr(p, "text", "")])
                
                if not response_text:
                    response_text = getattr(last_message_event, "text", "") or getattr(last_message_event, "output", "") or ""

            # Collect any generated files from the session state
            if session.state and isinstance(session.state, dict):
                generated_files = session.state.get("generated_files", [])

        # Map generated files to FileItem
        files = []
        for f in generated_files:
            filename = os.path.basename(f)
            file_type = "presentation" if filename.endswith(".pptx") else "audio" if filename.endswith(".mp3") else "video"
            files.append(FileItem(
                path=f"/static/{filename}",
                type=file_type,
                name=filename
            ))
            
        logger.info(f"Request processed. Found {len(files)} files.")
        return ResearchResponse(content=response_text, files=files)

    except Exception as e:
        logger.error(f"Error processing research request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/threads/{session_id}")
async def delete_thread(session_id: str, agent_type: Optional[str] = 'exploration', user_id: str = Depends(get_current_user)):
    target_app_name = f"aletheia_{agent_type}" if agent_type else adk_app.name
    try:
        await session_service.delete_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
        return {"status": "success", "message": f"Thread {session_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting thread {session_id}: {e}")
        # Try finding in default app just in case
        try:
            await session_service.delete_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/threads")
async def get_user_threads(radar_id: Optional[str] = None, agent_type: Optional[str] = 'exploration', user_id: str = Depends(get_current_user)):
    target_app_name = f"aletheia_{agent_type}" if agent_type else adk_app.name
    try:
        threads = []
        session_list_fn = getattr(session_service, "list_sessions_for_user", None)

        if callable(session_list_fn):
            sessions = await session_list_fn(user_id=user_id, app_name=target_app_name, radar_id=radar_id)
            
            # Merge legacy sessions (from default 'Aletheia' app scope) to prevent history loss
            if target_app_name != adk_app.name:
                try:
                    legacy_sessions = await session_list_fn(user_id=user_id, app_name=adk_app.name, radar_id=radar_id)
                    # Deduplicate based on session ID
                    if sessions is None:
                        sessions = []
                    existing_ids = set()
                    for s in sessions:
                        sid = getattr(s, "session_id", None) or getattr(s, "id", None)
                        if isinstance(s, dict):
                            sid = s.get("session_id") or s.get("id")
                        if sid:
                            existing_ids.add(sid)
                            
                    for ls in legacy_sessions or []:
                        ls_id = getattr(ls, "session_id", None) or getattr(ls, "id", None)
                        if isinstance(ls, dict):
                            ls_id = ls.get("session_id") or ls.get("id")
                        
                        if ls_id and ls_id not in existing_ids:
                            sessions.append(ls)
                except Exception as ex:
                    logger.warning(f"Failed to fetch legacy threads: {ex}")

            for s in sessions or []:
                if isinstance(s, dict):
                    raw_state = s.get("state") or {}
                    session_id = s.get("session_id") or s.get("id")
                    title = raw_state.get("title") or s.get("title") or "Untitled Research"
                else:
                    raw_state = getattr(s, "state", None) or {}
                    session_id = getattr(s, "session_id", None) or getattr(s, "id", None)
                    title = (raw_state.get("title") if isinstance(raw_state, dict) else None) or getattr(s, "title", None) or "Untitled Research"

                if session_id:
                    # Filter out internal/system sessions
                    # 1. Check ID pattern (sync_*)
                    if str(session_id).startswith("sync_"):
                        continue
                    # 2. Check Title pattern (System sweeping/thinking)
                    if str(title).startswith("System sweeping") or str(title).startswith("System thinking"):
                        continue

                    threads.append({
                        "id": session_id, 
                        "title": title,
                        "radarId": raw_state.get("radar_id")
                    })
            return {"threads": threads}
        return {"threads": []}
    except Exception as e:
        logger.error(f"Error fetching threads: {e}")
        return {"threads": []}

@app.post("/api/user/init")
async def init_user_data(user_id: str = Depends(get_current_user)):
    """
    Initializes the user's data structures in Firestore (Radar, Exploration, Projects).
    """
    from app.db import user_data_service
    try:
        await user_data_service.initialize_user_collections(user_id)
        return {"status": "success", "message": f"User {user_id} initialized."}
    except Exception as e:
        logger.error(f"Error initializing user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize user data")

from app.schemas import RadarCreate

@app.post("/api/radars", response_model=Dict[str, str])
async def create_radar(radar: RadarCreate, user_id: str = Depends(get_current_user)):
    logger.info(f"Creating radar for user {user_id}: {radar.title}")
    from app.db import user_data_service
    try:
        # Validate frequency
        if radar.frequency not in ["Daily", "Weekly", "Monthly"]:
            raise HTTPException(status_code=400, detail="Invalid frequency. Must be 'Daily', 'Weekly', or 'Monthly'.")

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

@app.get("/api/radars")
async def get_radars(user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
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

@app.get("/api/radars/briefing")
async def get_radar_briefing(radar_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    """
    Returns a briefing message for the Research Radar view.
    - If no radar_id and no radars: Returns a capability description.
    - If no radar_id but has radars: Returns a summary of all radar updates.
    - If radar_id: Returns a summary for that specific radar based on scenarios:
        2.1 Existing work (viewed): Welcome back + summary + continue.
        2.2 New parse (unviewed): Time since last review + new info + start.
        2.3 New radar (no parse): Welcome + sweep prompt.
    """
    from app.db import user_data_service
    try:
        if radar_id:
            radar_doc = await user_data_service.get_radar_collection(user_id).document(radar_id).get()
            if not radar_doc.exists:
                return {"summary": "Radar configuration not found."}
            
            data = radar_doc.to_dict()
            name = data.get('title', 'this radar')
            summary = data.get('latest_summary')
            last_updated = data.get('lastUpdated')
            last_viewed = data.get('lastViewed')

            # Track view immediately
            await user_data_service.track_radar_viewed(user_id, radar_id)

            # Scenario 2.3: No parse ever happened
            if not last_updated:
                return {
                    "scenario": "new",
                    "summary": f"Welcome to the **{name}** radar! I am ready to monitor this space for you. Would you like to start with an initial sweep to see what's currently trending?"
                }

            # Scenario 2.2: New parse that user hasn't reviewed
            # (last_updated exists and either no last_viewed OR last_updated is newer than last_viewed)
            is_new_parse = not last_viewed or last_updated > last_viewed
            if is_new_parse:
                return {
                    "scenario": "unviewed",
                    "summary": f"It's been a while since you last reviewed the updates for **{name}**. I've found some new developments since {last_viewed or 'you started'}:\n\n{summary}\n\nWhere would you like to start exploring?"
                }

            # Scenario 2.1: Pickup existing work
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
        return {
            "summary": f"Welcome back! Your radars are actively monitoring **{', '.join(titles)}**. Which one would you like to dive into today?"
        }
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        return {"summary": "Ready to track your research updates."}

@app.post("/api/radars/{radar_id}/sync")
async def sync_radar(radar_id: str, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    """
    Triggers a proactive sweep of the latest information for a specific radar.
    """
    logger.info(f"Sync requested for radar {radar_id} by user {user_id}")
    background_tasks.add_task(execute_radar_sync, user_id, radar_id)
    return {"message": "Sync started in background."}

async def execute_radar_sync(user_id: str, radar_id: str):
    from app.db import user_data_service
    from app.tools import current_user_id, current_radar_id
    from google.adk.runners import Runner
    
    # Set context for the background tool execution
    current_user_id.set(user_id)
    current_radar_id.set(radar_id)
    
    try:
        # 1. Fetch radar config
        radar_doc = await user_data_service.get_radar_collection(user_id).document(radar_id).get()
        if not radar_doc.exists:
            logger.error(f"Sync failed: Radar {radar_id} not found")
            return
        
        radar_data = radar_doc.to_dict()
        
        # 2. Get real papers from Arxiv
        from app.tools import search_arxiv
        
        arxiv_config = radar_data.get('arxivConfig') or {}
        search_query = ""
        
        # Build search query from config
        terms = []
        if arxiv_config.get('categories'):
            categories = arxiv_config.get('categories')
            if isinstance(categories, list):
                cat_part = " OR ".join([f"cat:{c}" for c in categories])
                terms.append(f"({cat_part})")
        
        if arxiv_config.get('keywords'):
            keywords = arxiv_config.get('keywords')
            if isinstance(keywords, list):
                kw_part = " OR ".join([f"all:{k}" for k in keywords])
                terms.append(f"({kw_part})")
        
        if terms:
            search_query = " AND ".join(terms)
        else:
            search_query = radar_data.get('title')

        logger.info(f"Running real Arxiv search for radar {radar_id} with query: {search_query}")
        real_papers = search_arxiv(query=search_query, max_results=6, sort_by_date=True)
        
        if real_papers:
            # We no longer store the raw papers as captured items.
            # Instead, we just pass them to the agent to generate summaries.
            logger.info(f"Found {len(real_papers)} prospective papers for radar {radar_id}")
            for i, paper in enumerate(real_papers, 1):
                logger.info(f"  Paper {i}: {paper.get('title', 'N/A')} by {', '.join(paper.get('authors', [])[:3])}")
        else:
            logger.info(f"No papers found for radar {radar_id}")

        # 3. Call Agent (Internal Runner)
        # We pass the metadata of found papers so the agent can synthesize and SAVE refined summaries/audio
        query = f"SYSTEM DIRECTIVE: You MUST perform a research briefing for the following Radar.\n"
        query += f"TARGET_TITLE: **{radar_data.get('title')}**\n"
        query += f"TARGET_RADAR_ID: **{radar_id}**\n\n"
        
        if real_papers:
            query += f"I have found {len(real_papers)} new papers from Arxiv:\n"
            query += json.dumps(real_papers, indent=2)
            query += f"\n\nCRITICAL INSTRUCTION: You MUST call the `save_radar_item` tool for EACH paper found. Use the exact ID '{radar_id}' for the `unique_topic_token` argument. Do NOT claim the ID is None. The ID is provided right here: {radar_id}.\n"
            query += "\nFor each call, provide the specific paper title as `item_title`, a detailed academic digest (3-4 paragraphs) as `item_summary`, the list of authors as `authors`, and the PDF URL as `source_url`."
            query += "\n\nFINAL OUTPUT REQUIREMENT: "
            query += "After saving all items, your final text response MUST be a concise but informative 'Briefing Update' for the user. "
            query += "It should state: 'I found X new papers.' followed by a bulleted list of the papers found with a 1-sentence topic summary for each. "
            query += "Do not just say 'I have saved the items'. Give the user the high-level news."
        else:
            query += "No new Arxiv papers were found in the immediate sweep, but please check other sources for any significant updates and synthesize a report."
            
        job_session_id = f"sync_{radar_id}_{uuid.uuid4().hex[:8]}"
        # For background sync, we also need to use the correct app name if we want consistency, 
        # but 'sync' is typically internal. However, consistently using 'aletheia-radar' is better.
        target_sync_app_name = "aletheia_radar"
        
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

        # 4. Fetch the final session to get the full assistant response and update summary
        final_session = await session_service.get_session(user_id=user_id, session_id=job_session_id, app_name=target_sync_app_name)
        if final_session and final_session.events:
            for event in reversed(final_session.events):
                if getattr(event, "role", None) == "assistant":
                    content_attr = getattr(event, "content", None)
                    if content_attr and hasattr(content_attr, "parts") and content_attr.parts:
                        response_text = "\n".join([str(p.text or "") for p in content_attr.parts if hasattr(p, "text") and p.text])
                        break
        
        if not response_text:
            response_text = f"The research sweep for {radar_data.get('title')} is complete."

        # Note: save_radar_item tool (called by agent) already handles updating the radar summary and capturedCount.
        # But we ensure it's established here if the agent didn't call it for some reason.
        await user_data_service.save_radar_summary(user_id, radar_id, response_text, captured_inc=0)
        logger.info(f"Proactive sync completed for radar {radar_id}")

    except Exception as e:
        logger.error(f"Error in background sync for {radar_id}: {e}", exc_info=True)

@app.put("/api/radars/{radar_id}", response_model=Dict[str, str])
async def update_radar(radar_id: str, radar: RadarCreate, user_id: str = Depends(get_current_user)):
    logger.info(f"Updating radar {radar_id} for user {user_id}")
    from app.db import user_data_service
    try:
        if radar.frequency not in ["Daily", "Weekly"]:
            raise HTTPException(status_code=400, detail="Invalid frequency. Must be 'Daily' or 'Weekly'.")

        data = radar.model_dump()
        data["lastUpdated"] = "Just updated"
        
        await user_data_service.update_radar_item(user_id, radar_id, data)
        return {"message": "Radar updated successfully"}
    except Exception as e:
        logger.error(f"Error updating radar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/radars/{radar_id}", response_model=Dict[str, str])
async def delete_radar(radar_id: str, user_id: str = Depends(get_current_user)):
    logger.info(f"Deleting radar {radar_id} for user {user_id}")
    from app.db import user_data_service
    try:
        await user_data_service.delete_radar_item(user_id, radar_id)
        return {"message": "Radar deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting radar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/radars/{radar_id}/read")
async def mark_radar_read(radar_id: str, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    await user_data_service.reset_radar_unread(user_id, radar_id)
    return {"status": "success"}

@app.post("/api/radars/{radar_id}/status")
async def update_radar_status(radar_id: str, status: str, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    if status not in ["active", "paused"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    await user_data_service.update_radar_status(user_id, radar_id, status)
    return {"status": "success"}

@app.get("/api/radars/{radar_id}/items")
async def get_radar_items(radar_id: str, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    items = await user_data_service.get_radar_captured_items(user_id, radar_id)
    logger.info(f"Fetched {len(items)} items for radar {radar_id} and user {user_id}")
    return items

@app.delete("/api/radars/{radar_id}/items/{item_id}")
async def delete_radar_item(radar_id: str, item_id: str, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    await user_data_service.delete_radar_captured_item(user_id, radar_id, item_id)
    return {"status": "success"}

@app.post("/api/exploration/save")
async def save_to_exploration(item: dict, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    import httpx
    try:
        # Check if we have a URL to download
        source_url = item.get("url") or item.get("pdf_url")
        if source_url:
            try:
                # Determine extension
                ext = "html"
                if source_url.lower().endswith(".pdf"):
                    ext = "pdf"
                
                logger.info(f"Downloading content from {source_url}...")
                async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                    resp = await client.get(source_url)
                    if resp.status_code == 200:
                        # Check content-type header to confirm PDF
                        ct = resp.headers.get("content-type", "").lower()
                        if "application/pdf" in ct:
                            ext = "pdf"
                        
                        # Generate filename
                        safe_title = "".join([c if c.isalnum() else "_" for c in item.get("title", "untitled")])[:50]
                        filename = f"expl_{uuid.uuid4().hex[:8]}_{safe_title}.{ext}"
                        local_path = os.path.join(STATIC_DIR, "docs", filename)
                        
                        # Write to file
                        mode = "wb"
                        with open(local_path, mode) as f:
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

@app.post("/api/exploration/upload")
async def upload_exploration_item(
    title: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    from app.db import user_data_service
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

@app.get("/api/exploration")
async def get_exploration_items(user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    try:
        items = await user_data_service.get_exploration_items(user_id)
        return {"items": items}
    except Exception as e:
        logger.error(f"Error fetching exploration items: {e}")
        return {"items": []}

@app.put("/api/exploration/{item_id}/archive")
async def archive_exploration_item(item_id: str, archived: bool, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    try:
        await user_data_service.update_exploration_item(user_id, item_id, {"isArchived": archived})
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error archiving item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/exploration/{item_id}")
async def delete_exploration_item(item_id: str, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    try:
        await user_data_service.delete_exploration_item(user_id, item_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting exploration item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/save")
async def save_to_project(item: dict, user_id: str = Depends(get_current_user)):
    from app.db import user_data_service
    try:
        # We might want to remove 'id' if successful to create a NEW id for the project item? 
        # Or keep it as a reference? Usually standard to clean 'id' before adding new doc.
        item_data = item.copy()
        if "id" in item_data:
            del item_data["id"]
        
        await user_data_service.add_project_item(user_id, item_data)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving to project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}")
async def get_session_history(session_id: str, agent_type: Optional[str] = 'exploration', user_id: str = Depends(get_current_user)):
    target_app_name = f"aletheia_{agent_type}" if agent_type else adk_app.name
    try:
        session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=target_app_name)
        
        # If not found, try fallback to default app (for legacy sessions created before separation)
        if not session:
            try:
                session = await session_service.get_session(user_id=user_id, session_id=session_id, app_name=adk_app.name)
            except:
                pass
        
        if not session:
            return {"messages": []}
        
        # Prepare pools for matching files to messages
        history = []
        gen_files = session.state.get("generated_files", []) or []
        uploaded_files = session.state.get("uploaded_files", []) or []
        unassigned_uploads = list(uploaded_files)
        unassigned_generated = list(gen_files)
        
        logger.info(f"Loading history for session {session_id}. State has {len(uploaded_files)} uploads and {len(gen_files)} generated files.")
        
        for event in session.events:
            text = ""
            content = getattr(event, "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    # Filter out the scrubbed file placeholder from the UI text
                    text_parts = []
                    for p in parts:
                        p_text = getattr(p, "text", "")
                        # Handle potential None value from valid but empty attribute
                        p_text_str = str(p_text or "")
                        if p_text_str and "[External file data not preserved in history]" not in p_text_str:
                            text_parts.append(p_text_str)
                    text = "\n".join(text_parts)
            
            if not text:
                # Still check event level text but filter placeholder
                raw_text = getattr(event, "text", "") or getattr(event, "output", "") or ""
                if "[External file data not preserved in history]" not in str(raw_text):
                    text = raw_text
            
            # If after filtering there is no text AND no files (checked later), we might still want to show the bubble
            # if it was an upload-only message.
            
            # Improved role detection for ADK Events
            role = None
            
            # 1. Check direct 'author' attribute (common in ADK Event objects)
            author = getattr(event, "author", None)
            if author:
                author_str = str(author).lower()
                if "user" in author_str:
                    role = "user"
                elif any(m in author_str for m in ("assistant", "model", "aletheia")):
                    role = "assistant"
                elif "system" in author_str:
                    role = "system"
                elif "tool" in author_str:
                    role = "tool"

            # 2. Check 'role' attribute if 'author' didn't yield a standard role
            if not role:
                role = getattr(event, "role", None)
                if isinstance(role, str):
                    role = role.lower()
            
            # 3. Check within content (Gemini type events)
            if not role and content:
                role = getattr(content, "role", None)
                if isinstance(role, str):
                    role = role.lower()

            # 4. Final heuristic fallback
            if role not in ("user", "assistant", "system", "tool"):
                event_type = str(getattr(event, "type", "") or getattr(event, "event_type", "")).lower()
                if any(k in event_type for k in ("user", "input", "request")):
                    role = "user"
                elif "thought" in text.lower() or "thinking" in event_type or "tool" in event_type:
                    # Check if this is a user-facing tool output that should be shown
                    # We look for specific function names in the event or tool usage metadata
                    # Note: ADK events might store tool name in 'function_name' or similar
                    is_user_facing = False
                    tool_name = getattr(event, "tool_name", "") or getattr(event, "function_name", "") or ""
                    
                    # If not direct attribute, try to find it in tool_calls of previous event? 
                    # Simpler approach: Check if text looks like a file path output from our known tools
                    # or if the tool_name was captured.
                    if any(t in tool_name for t in ["generate_audio_summary", "generate_presentation_file", "generate_video_lecture_file"]):
                         is_user_facing = True
                    
                    # Also content heuristics for tool outputs that are just file paths
                    if text.strip().endswith(".mp3") or text.strip().endswith(".pptx") or text.strip().endswith(".mp4"):
                        if "/static/" in text or "http" in text:
                            is_user_facing = True

                    if is_user_facing:
                        role = "assistant" # Show as assistant message
                    else:
                        role = "tool"  # Treat as internal tool/system log
                else:
                    # If we really can't tell, don't show it. Better to miss a weird message than show garbage.
                    role = "unknown"

            # 5. STRICT FILTER: Only show User and Assistant messages in UI
            if role not in ("user", "assistant"):
                continue
            
            # Extract files if any
            files = []
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    for p in parts:
                        if hasattr(p, "inline_data"):
                            # This is an uploaded file
                            # Note: Data might be scrubbed, but we still want the name/type
                            # For now, we can only reasonably restore generated files with paths
                            pass
            
            # ADK often stores generated files in session.state['generated_files']
            # We'll check if this specific event (if it's the final assistant response) 
            # matches the generated files.
            
            # Match files to this specific message using consumption logic
            msg_files = []
            
            # 1. Match Uploaded Files (User role)
            # We count scrubbed parts to know how many files to pull from the session pool
            if role == "user" and content:
                scrubbed_count = 0
                for p in getattr(content, "parts", []):
                    p_val = getattr(p, "text", "")
                    if "[External file data not preserved in history]" in str(p_val or ""):
                        scrubbed_count += 1
                
                for _ in range(scrubbed_count):
                    if unassigned_uploads:
                        up = unassigned_uploads.pop(0)
                        if isinstance(up, dict):
                            msg_files.append({
                                "path": up.get("path"),
                                "type": "pdf" if up.get("path", "").lower().endswith(".pdf") else "other",
                                "name": up.get("name")
                            })

            # 2. Match Generated Files (Assistant role)
            # Usually assistant responses follow a tool call that generates files.
            # If the response text mentions synthesis or files, we assign from the generated pool.
            if role == "assistant":
                # Heuristic: if this is a synthesis message, it likely corresponds to the latest generated files
                # For now, if we have unassigned generated files, we assign them to the next assistant message
                if unassigned_generated:
                    # Assistant messages usually come one by one after Turn/Tool events.
                    # We'll take ALL currently unassigned generated files if this message looks final.
                    if text.strip() == "Research synthesis complete." or "report" in text.lower():
                        while unassigned_generated:
                            f = unassigned_generated.pop(0)
                            path = f if isinstance(f, str) else f.get("path")
                            name = os.path.basename(path) if isinstance(f, str) else f.get("name", os.path.basename(path))
                            msg_files.append({
                                "path": path if path.startswith("/") or "://" in path else f"/{path}",
                                "type": "pdf" if path.lower().endswith(".pdf") else "other",
                                "name": name
                            })

            # Clean up User prompts that include internal context or directives
            if role == "user":
                # 1. Hide System Directives (automated Radar syncs)
                if "SYSTEM DIRECTIVE:" in text:
                    text = "" # Will be skipped below if no files
                
                # 2. Strip Context Injection (Exploration/Radar Chat)
                elif "CONTEXT:" in text and "User Query:" in text:
                    import re
                    match = re.search(r"User Query:\s*(.*)", text, re.DOTALL)
                    if match:
                        text = match.group(1).strip()

            # Skip messages with no text AND no files (common for internal tool calls that don't output text)
            if not text.strip() and not msg_files:
                continue

            history.append({
                "id": str(event.id),
                "role": role,
                "content": text,
                "timestamp": event.timestamp,
                "files": msg_files
            })
            
        # Collect all session-wide documents
        all_docs = []
        # 1. From generated files
        for f in gen_files:
            path = f if isinstance(f, str) else f.get("path")
            name = os.path.basename(path) if isinstance(f, str) else f.get("name", os.path.basename(path))
            
            if path and (path.lower().endswith(".pdf") or (isinstance(f, dict) and f.get("type") == "pdf")):
                all_docs.append({
                    "name": name,
                    "url": path if path.startswith("/") or "://" in path else f"/{path}"
                })
        
        # 2. From specifically tracked uploaded files
        for f in uploaded_files:
            if isinstance(f, dict) and f.get("type") == "pdf":
                path = f.get("path")
                all_docs.append({
                    "name": f.get("name"),
                    "url": path if path.startswith("/") or "://" in path else f"/{path}"
                })

        return {
            "messages": history,
            "documents": all_docs
        }
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}", exc_info=True)
        return {"messages": []}

# Serve Frontend
if os.path.exists("dist"):
    logger.info("Serving production frontend from 'dist' directory.")
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Explicitly check if the file exists in the 'dist' directory
        # This handles assets like favicon.ico, manifest.json, etc.
        dist_file_path = os.path.join("dist", full_path)
        if full_path and os.path.isfile(dist_file_path):
            from fastapi.responses import FileResponse
            return FileResponse(dist_file_path)
            
        # If it's an API or Static path that reached here, it means the specific 
        # routes/mounts didn't catch it. We should 404 instead of returning index.html
        if full_path.startswith("api/") or full_path.startswith("static/"):
            logger.warning(f"Static/API request fall-through to catch-all: {full_path}")
            raise HTTPException(status_code=404, detail=f"The requested asset '{full_path}' was not found.")
        
        # SPA fallback: Send index.html for any other route to let React handle it
        from fastapi.responses import FileResponse
        index_path = "dist/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
        return HTTPException(status_code=404, detail="Application entry point (index.html) not found.")
else:
    logger.warning("'dist' directory not found. Frontend will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
