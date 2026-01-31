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
    generate_video_lecture_file
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
    
    EVALUATION CRITERIA:
    1. **Content Timeliness**: Ensure you find the latest developments, industry trends, and application cases.
    2. **Knowledge Extension**: Connect basic knowledge boundaries to cutting-edge research and real-time background.
    3. **Research Completeness**: Form a complete knowledge chain from fundamentals to latest theoretical advances.
    
    GUIDELINES:
    - Use `web_search` for real-time information, industry cases, and current application status.
    - Use `search_arxiv` for cutting-edge academic research and theoretical advances.
    - **Depth over Breadth**: When investigating a topic, ensure you cover Concept Definition, Core Principles, Key Formulas/Algorithms (if applicable), Application Scenarios, and Limitations.
    
    Provide a comprehensive, well-structured summary of your findings that meets these deep research standards.""",
    tools=[web_search, search_arxiv],
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

# 5. Data Collection / Research Radar Agent
data_collection_agent = Agent(
    name="data_collection_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are a Data Collection Specialist (Research Radar).
    
    Your goal is to collect research articles, postings, and updates from various sources including:
    - Arxiv (via `search_arxiv`)
    - Tech Blogs, Medium, News Sites (via `web_search` to find links, then `scrape_website` to read content)
    - Social Media discussions (via `web_search`)
    
    FREQUENCY & MONITORING:
    - If the user specifies a frequency (e.g., "daily", "weekly"), acknowledge this request.
    - Organize your findings into a clear 'Research Radar' report.
    - Categorize items by source type (Academic, Industry Blog, Social Media, etc.).
    
    When collecting data:
    1. Search for the latest content matching the user's topic.
    2. Filter for high-quality, relevant items.
    3. Use `scrape_website` to get details if the summary is insufficient.
    4. Compile the report with titles, summaries, and source URLs.
    """,
    tools=[web_search, search_arxiv, scrape_website],
)

# Root Router Agent
root_agent = Agent(
    name="aletheia_router",
    model=Gemini(model="gemini-2.5-flash", api_key=api_key),
    instruction="""You are the Main Coordinator of Aletheia, a multimedia research assistant.
    Your job is to understand the user's request and delegate to the appropriate specialist.
    
    SPECIALISTS:
    1. `search_specialist`: Use this for deep research and information gathering.
    2. `data_collection_specialist`: Use this for "Research Radar" tasks, collecting articles/feed updates, or monitoring specific sources (Arxiv, blogs, etc.) over time.
    3. `audio_specialist`: Use this when the user explicitly asks for audio, MP3, or a "podcast".
    4. `presentation_specialist`: Use this when the user asks for slides, PPTX, or a presentation.
    5. `video_specialist`: Use this when the user asks for a video or MP4.
    
    DELEGATION STRATEGY:
    - For initial research -> Delegate to `search_specialist`.
    - For "updates", "feeds", "collection", or "radar" requests -> Delegate to `data_collection_specialist`.
    - For creating specific multimedia output -> Delegate to the corresponding specialist.
    - If a user asks to "collect X and make a video", first collect data, then pass results to the video specialist.
    
    Always provide a helpful final response to the user, including links to any generated files.
    """,
    sub_agents=[search_agent, data_collection_agent, audio_agent, presentation_agent, video_agent],
)

app = App(root_agent=root_agent, name="Aletheia")
