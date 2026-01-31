# ruff: noqa
import os
import logging
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.models import Gemini
from app.tools import (
    web_search, 
    search_arxiv, 
    scrape_website,
    generate_audio_summary, 
    generate_presentation_file, 
    generate_video_lecture_file,
    list_radars,
    get_radar_details,
    save_radar_results
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback for API Key naming
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("No Gemini API key found in environment variables (GOOGLE_API_KEY or GEMINI_API_KEY)")

# Specialized Sub-Agents

# 1. Search Specialist (Handles both web and academic research)
search_agent = Agent(
    name="search_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are a Deep Research Strategy Expert.
    
    Your goal is to provide a "deep research" standard of information, not just surface coverage.
    
    GUIDELINES:
    - Use `web_search` for real-time information, industry cases, and current application status.
    - Use `search_arxiv` for cutting-edge academic research and theoretical advances.
    - Use `scrape_website` to extract full content when useful.
    - **Depth over Breadth**: Cover Concept Definition, Core Principles, Key Formulas/Algorithms (if applicable), Application Scenarios, and Limitations.
    """,
    tools=[web_search, search_arxiv, scrape_website],
)

# 2. Audio Content Creator
audio_agent = Agent(
    name="audio_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are an Audio Content Creator.
    Use `generate_audio_summary` to create a spoken summary of the provided text.
    Return the path to the generated MP3 file.""",
    tools=[generate_audio_summary],
)

# 3. Presentation Designer
presentation_agent = Agent(
    name="presentation_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are a Presentation Designer.
    Use `generate_presentation_file` to create a slide deck from the provided content.
    Return the path to the generated PPTX file.""",
    tools=[generate_presentation_file],
)

# 4. Video Producer
video_agent = Agent(
    name="video_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are a Video Producer.
    Use `generate_video_lecture_file` to create a narrated video lecture.
    Return the path to the generated MP4 file.""",
    tools=[generate_video_lecture_file],
)

# 5. Research Radar Specialist
research_radar_agent = Agent(
    name="research_radar_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are the Research Radar Specialist. 
    Your domain is managing and executing user-defined research radars.
    
    CAPABILITIES:
    - Use `list_radars` to see all topics the user is tracking.
    - Use `get_radar_details` to get the specific Arxiv filters, keywords, and custom prompts for a radar.
    - Use `search_arxiv`, `web_search`, and `scrape_website` to collect the latest information.
    - Use `save_radar_results` to store summaries or findings back to the radar history.
    
    GUIDELINES:
    1. If the user asks for a report on a radar, fetch its details first.
    2. Respect the 'Arxiv Configuration' (categories, authors) and 'Custom Prompt' instructions found in the radar settings.
    3. Return a comprehensive summary of findings. Your task is to gather and synthesize; the coordinator will handle specific media conversions (Audio, PPT) if requested.
    """,
    tools=[list_radars, get_radar_details, save_radar_results, web_search, search_arxiv, scrape_website],
)

# 6. Exploration Specialist
exploration_agent = Agent(
    name="exploration_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are an Exploration & Discovery Expert.
    Your goal is to help users browse and discover new research trends.
    (Note: This module is under development. For now, provide helpful search summaries).
    """,
    tools=[web_search, search_arxiv, scrape_website],
)

# 7. Project Specialist
project_agent = Agent(
    name="project_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are a Project Management Assistant.
    Your goal is to organize research artifacts, papers, and summaries into projects.
    (Note: This module is under development).
    """,
    tools=[],
)

# Root Router Agent
root_agent = Agent(
    name="aletheia_router",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are the Main Coordinator of Aletheia, a multimedia research intelligence system.
    Your job is to understand the user's intent and delegate to the right specialist based on the current view or request.
    
    SPECIALISTS:
    1. `research_radar_specialist`: Use this for ANYTHING related to "Research Radar", managing radars, or running configured research feeds.
    2. `exploration_specialist`: Use this for general browsing, discovery, and surface-level research.
    3. `search_specialist`: Use this for "Deep Research" requests that require intense, multi-source investigation.
    4. `project_specialist`: Use this for managing research artifacts, files, and project organization.
    
    DELEGATION STRATEGY:
    - If the user is in the 'Radar' view (CONTEXT) or asks about radars -> Delegate to `research_radar_specialist`.
    - If the user asks for a "Deep Search" or detailed technical investigation -> `search_specialist`.
    - Format conversion (Audio, PPT, Video): After a specialist provides research information, you may further delegate to `audio_specialist`, `presentation_specialist`, or `video_specialist` if the user's radar settings or message specify those formats.
    
    Always provide a helpful and encouraging final response, ensuring links to any generated files are included.
    """,
    sub_agents=[research_radar_agent, exploration_agent, search_agent, project_agent, audio_agent, presentation_agent, video_agent],
)

app = App(root_agent=root_agent, name="Aletheia")
