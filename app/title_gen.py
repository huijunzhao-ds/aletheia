import os
import logging
from google.genai import types, Client

logger = logging.getLogger(__name__)

async def generate_smart_title(query: str) -> str:
    """
    Generates a short, relevant title for the research session based on the user's query.
    """
    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return query[:50] + "..." if len(query) > 50 else query

        client = Client(api_key=api_key)
        
        prompt = f"""
        Task: Create a short, professional title (3-6 words) for a research session based on the user's query.
        Constraints:
        - Do not use quotes.
        - Do not act as the user.
        - Summarize the core topic.
        
        Query: {query}
        Title:
        """
        
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-exp",
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=20,
            ),
            contents=prompt
        )
        
        if response.text:
            cleaned_title = response.text.strip().replace('"', '').replace("'", "")
            return cleaned_title
            
        return query[:50]
    except Exception as e:
        logger.warning(f"Smart title generation failed: {e}")
        return query[:50] + "..." if len(query) > 50 else query
