
import logging
import os
import datetime
from google import genai
from google.genai import types
from app.core.user_data_service import user_data_service
from app.core.session_storage import session_service

logger = logging.getLogger(__name__)

class UserProfilingService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    async def _fetch_recent_chat_history(self, user_id: str, limit: int = 10) -> str:
        """Fetches recent user chat messages across apps to understand intent."""
        history_text = ""
        try:
            # We try to fetch from main apps.
            # In a real scenario, we might query all sessions or have a unified index.
            apps = ["Aletheia", "aletheia_radar", "aletheia_exploration", "aletheia_projects"]
            all_sessions = []
            
            for app_name in apps:
                sessions = await session_service.list_sessions_for_user(user_id=user_id, app_name=app_name)
                all_sessions.extend(sessions)
            
            # Sort by last_update_time desc
            all_sessions.sort(key=lambda x: x.last_update_time or 0, reverse=True)
            
            # Take recent sessions
            recent_sessions = all_sessions[:5]
            
            messages = []
            for sess in recent_sessions:
                # We only care about User messages for profiling interests
                for event in sess.events:
                    # Simple extraction: check for 'text' or parts
                    role = getattr(event, "role", "unknown")
                    # Try to deduce role if object doesn't have it explicitly or it varies
                    if not role or role == "unknown":
                         # Fallback heuristic based on type or source
                         if str(type(event)).lower().find("user") != -1: role = "user"

                    if role == "user" or (hasattr(event, "author") and "user" in str(event.author).lower()):
                        text = ""
                        content = getattr(event, "content", None)
                        if content and hasattr(content, "parts"):
                            for p in content.parts:
                                if hasattr(p, "text"):
                                    text += p.text + " "
                        elif hasattr(event, "text"):
                            text = event.text
                        
                        if text:
                            messages.append(f"User: {text[:200]}...") # Truncate for token efficiency

            # Return the last N messages
            history_text = "\n".join(messages[:limit])
            
        except Exception as e:
            logger.warning(f"Failed to fetch chat history: {e}")
            
        return history_text

    async def log_activity(self, user_id: str, activity_type: str, details: dict):
        """
        Logs a user activity.
        
        Args:
            user_id: The user ID.
            activity_type: Broad category (e.g., 'view_radar', 'click_paper', 'create_radar').
            details: Specific metadata (e.g., radar_title, paper_title, url).
        """
        try:
            data = {
                "type": activity_type,
                "details": details,
                # Timestamp added by user_data_service
            }
            await user_data_service.add_user_activity(user_id, data)
            
            # Trigger persona update periodically or on significant events?
            # For now, let's keep it manual or lazy. 
            # But maybe we want to trigger it every X events. 
            # For simplicity, we won't auto-trigger update here to avoid latency.
        except Exception as e:
            logger.error(f"Failed to log activity for {user_id}: {e}")

    async def update_user_persona(self, user_id: str):
        """
        Analyzes recent activities and updates the user's research persona.
        """
        if not self.client:
            logger.warning("No API key for UserProfilingService")
            return

        try:
            # 1. Fetch recent activities and chat history
            activities = await user_data_service.get_recent_user_activities(user_id, limit=50)
            if not activities:
                # Even if no click activities, we might have chat history.
                # But let's check both or proceed if one exists.
                pass 
                
            chat_history = await self._fetch_recent_chat_history(user_id, limit=20)
            
            if not activities and not chat_history:
                return

            # 2. Construct Prompt
            activity_text = ""
            if activities:
                for act in activities:
                    ts = act.get("timestamp")
                    ts_str = ts.strftime("%Y-%m-%d") if ts else ""
                    details = act.get("details", {})
                    activity_text += f"- [{ts_str}] {act.get('type')}: {details}\n"

            prompt = f"""You are a User Research Profiler.
            Analyze the following user activities and chat messages to build a 'Research Persona'.
            
            USER ACTIVITIES:
            {activity_text}
            
            RECENT CHAT MESSAGES:
            {chat_history}
            
            OUTPUT INSTRUCTIONS:
            Create a concise summary (3-5 sentences) describing:
            1. Their primary research interests (topics, fields).
            2. Their browsing style (deep dives vs. broad skimming).
            3. Any specific preferences (formats, sources).
            
            Keep it objective and focused on helping a recommendation engine serving them.
            """

            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            
            persona = response.text
            
            # 3. Save
            await user_data_service.save_user_profile(user_id, persona)
            logger.info(f"Updated research persona for {user_id}")
            return persona

        except Exception as e:
            logger.error(f"Failed to update user persona: {e}")

    async def _generate_recommendation_reason(self, user_id: str, paper_entry: dict) -> str:
        """
        Generates a 1-2 sentence reason for recommending a paper based on user profile.
        """
        if not self.client:
            return ""

        try:
            # 1. Get User Profile
            profile = await user_data_service.get_user_profile(user_id)
            
            if not profile:
                # Fallback without triggering expensive/race-prone update in hot loop
                return "Recommended based on your radar settings."

            # 2. Get Recent Chat Context (Real-time interests)
            chat_history = await self._fetch_recent_chat_history(user_id, limit=5)

            # 3. Generate Reason
            paper_title = paper_entry.get("title")
            paper_summary = paper_entry.get("summary") or paper_entry.get("abstract") or ""

            prompt = f"""You are a Research Assistant.
            
            USER PROFILE:
            {profile}
            
            RECENT CHAT CONTEXT:
            {chat_history}
            
            PAPER:
            Title: {paper_title}
            Summary: {paper_summary[:500]}...
            
            TASK:
            Write a 1-2 sentence explanation of why this paper is relevant to this specific user.
            Connect the paper's content to the user's known interests or style.
            Directly address the user (e.g., "This aligns with your interest in...").
            """

            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7, tools=None)
            )
            
            return response.text.strip()

        except Exception as e:
            logger.error(f"Failed to generate recommendation reason: {e}")
    async def generate_recommendation_reason(self, user_id: str, paper_entry: dict) -> str:
        """
        Public wrapper for generating recommendation reasons.
        """
        return await self._generate_recommendation_reason(user_id, paper_entry)

# Singleton
user_profiling_service = UserProfilingService()

# --- Agent Tools ---
from app.services.context import current_user_id

async def get_research_persona() -> str:
    """
    Retrieves the current user's research persona/profile.
    This describes their research interests, style, and preferences based on their activity.
    """
    user_id = current_user_id.get()
    if not user_id: return "No user ID in context."
    return await user_data_service.get_user_profile(user_id)

async def update_research_persona() -> str:
    """
    Forces an update of the user's research persona based on recent activities.
    Returns the new persona.
    """
    user_id = current_user_id.get()
    if not user_id: return "No user ID in context."
    persona = await user_profiling_service.update_user_persona(user_id)
    return persona or "No activities found to generate persona."

