import os
import logging
import datetime
import json
from typing import List, Optional, Any, Dict
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.adk.sessions.in_memory_session_service import InMemorySessionService

logger = logging.getLogger(__name__)

def scrub_blobs(obj):
    """
    Recursively removes large binary data (base64 strings) from the session 
    to stay within Firestore's 1MB document limit.
    """
    if isinstance(obj, dict):
        if "inline_data" in obj and isinstance(obj["inline_data"], dict):
            blob = obj["inline_data"]
            if "data" in blob and isinstance(blob["data"], str) and len(blob["data"]) > 1024:
                # Use a valid base64 placeholder to avoid Pydantic validation errors on reload
                # 'REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ==' is base64 for 'DATA_STRIPPED_FOR_STORAGE'
                blob["data"] = "REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ=="
        return {k: scrub_blobs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [scrub_blobs(x) for x in obj]
    return obj

def rescue_blobs(obj):
    """
    Cleans up legacy invalid base64 placeholders to prevent validation crashes.
    """
    if isinstance(obj, dict):
        if "inline_data" in obj and isinstance(obj["inline_data"], dict):
            blob = obj["inline_data"]
            if "data" in blob and isinstance(blob["data"], str) and blob["data"].startswith("[Data stripped"):
                blob["data"] = "REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ=="
        return {k: rescue_blobs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [rescue_blobs(x) for x in obj]
    return obj

def remove_scrubbed_parts(obj):
    """
    Removes inline_data parts that contain the 'stripped' placeholder.
    This prevents the LLM from trying to process invalid file data in resumed sessions.
    """
    if isinstance(obj, dict):
        # If this is a 'content' object with 'parts'
        if "parts" in obj and isinstance(obj["parts"], list):
            new_parts = []
            for part in obj["parts"]:
                is_scrubbed = False
                if isinstance(part, dict):
                    if "inline_data" in part and isinstance(part["inline_data"], dict):
                        data = part["inline_data"].get("data")
                        if data == "REFUQV9TVFJJUFBFRF9GT1JfU1RPUkFHRQ==":
                            is_scrubbed = True
                
                if is_scrubbed:
                    # Replace the corrupted blob with a status message
                    new_parts.append({"text": "[External file data not preserved in history]"})
                else:
                    new_parts.append(remove_scrubbed_parts(part))
            obj["parts"] = new_parts
            return obj
        return {k: remove_scrubbed_parts(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [remove_scrubbed_parts(x) for x in obj]
    return obj

class FirestoreSessionService(BaseSessionService):
    """
    Custom Firestore-backed session service for Aletheia.
    Provides persistence for research threads and conversation history.
    """
    def __init__(self, collection_name="sessions"):
        try:
            from google.cloud import firestore
            database_id = os.getenv("FIREBASE_DATABASE_ID", "(default)")
            logger.info(f"Connecting to Firestore database: {database_id}")
            self.db = firestore.AsyncClient(database=database_id)
            self.collection_name = collection_name
            self.firestore_module = firestore
        except ImportError:
            logger.error("google-cloud-firestore not installed. FirestoreSessionService will not work.")
            raise

    async def get_session(self, *, user_id: str, session_id: str, app_name: str) -> Optional[Session]:
        doc = await self.db.collection(self.collection_name).document(session_id).get()
        if doc.exists:
            data = doc.to_dict()
            if data.get("user_id") == user_id and data.get("app_name") == app_name:
                # Deserialize events if they are stored as a JSON string
                events_data = data.get("events")
                if isinstance(events_data, str):
                    try:
                        data["events"] = json.loads(events_data)
                    except Exception as e:
                        logger.error(f"Failed to parse stringified events: {e}")
                        data["events"] = []
                # Rescue legacy invalid base64 strings
                data = rescue_blobs(data)
                # Remove scrubbed file parts before inference
                data = remove_scrubbed_parts(data)
                return Session.model_validate(data)
        return None

    async def create_session(self, *, user_id: str, session_id: str, app_name: str, state: Optional[Dict[str, Any]] = None, **kwargs) -> Session:
        session = Session(
            id=session_id,
            user_id=user_id,
            app_name=app_name,
            state=state or {},
            events=[],
            last_update_time=datetime.datetime.now(datetime.timezone.utc).timestamp()
        )
        data = session.model_dump(mode='json', exclude_none=True)
        # Scrub large blobs to stay under 1MB limit
        data = scrub_blobs(data)
        # Stringify events to bypass Firestore's nested array limitation
        data["events"] = json.dumps(data.get("events", []))
        await self.db.collection(self.collection_name).document(session_id).set(data)
        return session

    async def append_event(self, *, session: Session, event: Event) -> Event:
        session.events.append(event)
        ts = event.timestamp or datetime.datetime.now(datetime.timezone.utc)
        if hasattr(ts, 'timestamp'):
            ts = ts.timestamp()
        session.last_update_time = ts
        
        data = session.model_dump(mode='json', exclude_none=True)
        # Scrub large blobs to stay under 1MB limit
        data = scrub_blobs(data)
        # Stringify events to bypass Firestore's nested array limitation
        data["events"] = json.dumps(data.get("events", []))
        
        await self.db.collection(self.collection_name).document(session.id).set(data)
        return event

    async def update_session(self, *, user_id: str, session_id: str, app_name: str, state_update: Dict[str, Any]) -> None:
        doc_ref = self.db.collection(self.collection_name).document(session_id)
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            state = data.get("state", {})
            state.update(state_update)
            await doc_ref.update({"state": state})

    async def list_sessions(self, *, user_id: str, app_name: str, radar_id: Optional[str] = None) -> List[Session]:
        from google.cloud.firestore import FieldFilter
        
        query = self.db.collection(self.collection_name)\
            .where(filter=FieldFilter("user_id", "==", user_id))\
            .where(filter=FieldFilter("app_name", "==", app_name))
            
        if radar_id:
            query = query.where(filter=FieldFilter("state.radar_id", "==", radar_id))
        
        docs = query.stream()
        results = []
        async for doc in docs:
            data = doc.to_dict()
            events_data = data.get("events")
            if isinstance(events_data, str):
                try:
                    data["events"] = json.loads(events_data)
                except:
                    data["events"] = []
            # Rescue legacy invalid base64 strings
            data = rescue_blobs(data)
            # Remove scrubbed file parts before inference
            data = remove_scrubbed_parts(data)
            results.append(Session.model_validate(data))
        return results

    async def list_sessions_for_user(self, *, user_id: str, app_name: str, radar_id: Optional[str] = None) -> List[Session]:
        return await self.list_sessions(user_id=user_id, app_name=app_name, radar_id=radar_id)

    async def delete_session(self, *, user_id: str, session_id: str, app_name: str) -> None:
        await self.db.collection(self.collection_name).document(session_id).delete()

def get_session_service():
    """Initializes and returns the appropriate session service."""
    try:
        service = FirestoreSessionService()
        logger.info("Using custom FirestoreSessionService for storage")
        return service
    except Exception as e:
        logger.warning(f"Falling back to InMemorySessionService: {e}")
        service = InMemorySessionService()
        # Patch InMemorySessionService to support update_session and list_sessions_for_user
        if not hasattr(service, "update_session"):
            async def update_session_mock(*, user_id, session_id, app_name, state_update):
                sess = await service.get_session(user_id=user_id, session_id=session_id, app_name=app_name)
                if sess:
                    sess.state.update(state_update)
            service.update_session = update_session_mock
        
        if not hasattr(service, "list_sessions_for_user"):
            async def list_sessions_for_user_mock(*, user_id, app_name):
                return await service.list_sessions(user_id=user_id, app_name=app_name)
            service.list_sessions_for_user = list_sessions_for_user_mock
        return service
