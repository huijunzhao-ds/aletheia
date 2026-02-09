import os
import logging
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.models import Gemini
from app.services import (
    web_search, 
    search_arxiv, 
    scrape_website,
    generate_audio_summary, 
    generate_presentation_file, 
    generate_video_lecture_file,
    list_radars,
    get_radar_details,
    save_radar_item,
    list_exploration_items,
    read_local_file
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
    - Use `read_local_file` to read the full content of any PDF or file found in the 'To Review' list or previously saved.
    - Use `save_radar_item` to store a single research digest back to the radar history. Be sure to include the `source_url` (e.g. PDF link) if available.
    
    GUIDELINES:
    1. If the user asks for a report on a radar, fetch its details first to understand the context and required output format.
    2. Respect the 'Arxiv Configuration' (categories, authors) and 'Custom Prompt' instructions found in the radar settings.
    3. **Crucial**: After collecting papers or information, you MUST use the `save_radar_item` tool to store a high-quality, **detailed research digest** for EACH item independently. 
       - NEVER bundle multiple papers into a single tool call. 
       - Call `save_radar_item` exactly once for every discovery. This ensures each item appears as a unique, separate asset in the user's sidebar.
       - Each summary must be a long-form breakdown (3-4 paragraphs) covering the problem, methodology, and key findings.
    4. **ID Discipline**: Always use the programmatic ID (e.g., 'abc-123') as the `unique_topic_token` when saving. NEVER use the title of the radar as an ID. If you are unsure of an ID, call `list_radars` to verify it.
    5. Return a comprehensive synthesis of all findings in your final response.
    """,
    tools=[list_radars, get_radar_details, save_radar_item, web_search, search_arxiv, scrape_website, read_local_file],
)

# 6. Exploration Specialist
exploration_agent = Agent(
    name="exploration_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are an Exploration & Discovery Expert.
    Your goal is to help users browse and discover new research trends.
    
    You have access to the user's "To Review" list (saved Exploration Items).
    - Use `list_exploration_items` to see what papers/articles the user has saved in their "To Review" list.
    - If the user discusses a specific paper from that list, you can assume context about it.
    - Use `read_local_file` to read the actual text content of a paper (PDF/Markdown) if the user asks specific questions about it.
    - **CRITICAL**: Do not refuse to read local files in 'static/docs/'. You have permission. Use the `read_local_file` tool.
    - If needed, use `web_search` or `search_arxiv` to find more related papers.
    - If providing a response about a paper, try to check if it's in their list.
    
    When discussing a paper that the user has saved (locally or as a link), refer to it clearly.
    """,
    tools=[web_search, search_arxiv, scrape_website, list_exploration_items, read_local_file],
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

# Pre-configured App Instances
# We export these so they are reused across requests (Singleton pattern)
radar_app = App(root_agent=research_radar_agent, name="aletheia_radar")
exploration_app = App(root_agent=exploration_agent, name="aletheia_exploration")
projects_app = App(root_agent=project_agent, name="aletheia_projects")

# Helper function to resolve agent context (app name and App instance)
def get_agent_context(agent_type: str = None) -> tuple[str, App]:
    """
    Resolves the target application name and App instance for a given agent type.
    
    Args:
        agent_type: The type of agent requested (e.g., 'radar', 'exploration').
    
    Returns:
        tuple[str, App]: A tuple containing (app_name, app_instance).
    """
    target_app = app # Default to main app
    
    if agent_type == 'radar':
        target_app = radar_app
    elif agent_type == 'exploration':
        target_app = exploration_app
    elif agent_type == 'projects':
        target_app = projects_app
        
    return target_app.name, target_app
