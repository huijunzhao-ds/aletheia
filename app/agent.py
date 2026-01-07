# ruff: noqa
import os
import logging
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.models import Gemini
from app.tools import (
    web_search, 
    search_arxiv, 
    generate_audio_summary, 
    generate_presentation_file, 
    generate_video_lecture_file
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Specialized Sub-Agents

# 1. Search Specialist (Handles both web and academic research)
search_agent = Agent(
    name="search_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")),
    instruction="""You are a Search Specialist. 
    Use `web_search` for general information and current events.
    Use `search_arxiv` for scientific papers and academic research.
    Provide a comprehensive summary of your findings.""",
    tools=[web_search, search_arxiv],
)

# 2. Audio Content Creator
audio_agent = Agent(
    name="audio_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")),
    instruction="""You are an Audio Content Creator.
    Use `generate_audio_summary` to create a spoken summary of the provided text.
    Return the path to the generated MP3 file.""",
    tools=[generate_audio_summary],
)

# 3. Presentation Designer
presentation_agent = Agent(
    name="presentation_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")),
    instruction="""You are a Presentation Designer.
    Use `generate_presentation_file` to create a slide deck from the provided content.
    Return the path to the generated PPTX file.""",
    tools=[generate_presentation_file],
)

# 4. Video Producer
video_agent = Agent(
    name="video_specialist",
    model=Gemini(model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")),
    instruction="""You are a Video Producer.
    Use `generate_video_lecture_file` to create a narrated video lecture.
    Return the path to the generated MP4 file.""",
    tools=[generate_video_lecture_file],
)

# Root Router Agent
root_agent = Agent(
    name="aletheia_router",
    model=Gemini(model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")),
    instruction="""You are the Main Coordinator of Aletheia, a multimedia research assistant.
    Your job is to understand the user's request and delegate to the appropriate specialist.
    
    SPECIALISTS:
    1. `search_specialist`: Use this for any task that requires finding information (web or academic).
    2. `audio_specialist`: Use this when the user explicitly asks for audio, MP3, or a "podcast".
    3. `presentation_specialist`: Use this when the user asks for slides, PPTX, or a presentation.
    4. `video_specialist`: Use this when the user asks for a video or MP4.
    
    DELEGATION STRATEGY:
    - For initial research or information gathering -> Delegate to `search_specialist`.
    - For creating specific multimedia output -> Delegate to the corresponding specialist.
    - If a user asks for both (e.g., "Research X and make a video"), first delegate to `search_specialist` to get the context, then provide that context to the next specialist.
    
    Always provide a helpful final response to the user, including links to any generated files.
    """,
    sub_agents=[search_agent, audio_agent, presentation_agent, video_agent],
)

app = App(root_agent=root_agent, name="Aletheia")
