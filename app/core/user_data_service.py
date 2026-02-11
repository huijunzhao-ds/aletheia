import os
import logging
import datetime
from typing import Any, Dict
from google.cloud import firestore

logger = logging.getLogger(__name__)

class UserDataService:
    """
    Manages user-specific data collections for Research Radar, Exploration, and Projects.
    """
    def __init__(self):
        try:
            database_id = os.getenv("FIREBASE_DATABASE_ID", "(default)")
            project_id = os.getenv("VITE_FIREBASE_PROJECT_ID")
            
            key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "gcp-sa-key.json")
            if os.path.exists(key_path):
                self.db = firestore.AsyncClient.from_service_account_json(key_path, database=database_id)
                logger.info(f"Initialized Firestore Client using {key_path}")
            else:
                self.db = firestore.AsyncClient(database=database_id, project=project_id)
        except Exception as e:
            logger.error(f"Failed to initialize Firestore Client: {e}")
            self.db = None

    def _get_user_ref(self, user_id: str):
        if not self.db:
            raise RuntimeError("Firestore not initialized")
        return self.db.collection("users").document(user_id)

    async def initialize_user_collections(self, user_id: str):
        """
        Ensures the sub-collections for a user exist by creating placeholder metadata if needed.
        Firestore creates collections implicitly when documents are added, so this might just
        set a 'created_at' on the user document itself to establish the root.
        """
        if not self.db:
            return

        user_ref = self._get_user_ref(user_id)
        
        # We can just ensure the user document exists
        snapshot = await user_ref.get()
        if not snapshot.exists:
            await user_ref.set({
                "created_at": firestore.SERVER_TIMESTAMP,
                "user_id": user_id
            })
            logger.info(f"Initialized user root document for {user_id}")
        
    async def get_all_users(self):
        """
        Returns a list of all user IDs from the users collection.
        Used for global background sync tasks.
        """
        if not self.db:
            return []
        users = self.db.collection("users").stream()
        return [user.id async for user in users]
        
    # --- Research Radar ---
    def get_radar_collection(self, user_id: str):
        return self._get_user_ref(user_id).collection("radar")

    async def add_radar_item(self, user_id: str, item_data: Dict[str, Any]):
        return await self.get_radar_collection(user_id).add(item_data)

    async def get_radar_items(self, user_id: str):
        docs = self.get_radar_collection(user_id).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
        return results

    async def update_radar_item(self, user_id: str, radar_id: str, item_data: Dict[str, Any]):
        return await self.get_radar_collection(user_id).document(radar_id).update(item_data)

    async def delete_radar_item(self, user_id: str, radar_id: str):
        return await self.get_radar_collection(user_id).document(radar_id).delete()

    async def save_radar_summary(self, user_id: str, radar_id: str, summary: str, captured_inc: int = 0):
        update_data = {
            "latest_summary": summary,
            "lastUpdated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        }
        if captured_inc > 0:
            pass # capturedCount and unreadCount are deprecated
            
        return await self.get_radar_collection(user_id).document(radar_id).update(update_data)

    async def update_radar_status(self, user_id: str, radar_id: str, status: str):
        return await self.get_radar_collection(user_id).document(radar_id).update({
            "status": status
        })

    async def track_radar_viewed(self, user_id: str, radar_id: str):
        return await self.get_radar_collection(user_id).document(radar_id).update({
            "lastViewed": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        })

    def get_radar_items_collection(self, user_id: str, radar_id: str):
        return self.get_radar_collection(user_id).document(radar_id).collection("captured_items")

    async def add_radar_captured_item(self, user_id: str, radar_id: str, item_data: dict):
        # Use title or similar as a basis for ID or let it auto-generate
        doc_ref = self.get_radar_items_collection(user_id, radar_id).document()
        await doc_ref.set(item_data)
        return doc_ref.id

    async def get_radar_captured_items(self, user_id: str, radar_id: str):
        docs = self.get_radar_items_collection(user_id, radar_id).limit(20).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            # Sanitize for JSON: convert datetime/timestamps to strings
            for key, value in d.items():
                if hasattr(value, "isoformat"):
                    d[key] = value.isoformat()
                elif hasattr(value, "to_datetime"): # Handle Timestamp
                    d[key] = value.to_datetime().isoformat()
                    
            results.append(d)
        return results

    async def delete_radar_captured_item(self, user_id: str, radar_id: str, item_id: str):
        doc_ref = self.get_radar_items_collection(user_id, radar_id).document(item_id)
        await doc_ref.delete()
        return True

    async def get_all_radar_captured_keys(self, user_id: str, radar_id: str):
        """
        Efficiently retrieves only source_url and title of all captured items for deduplication.
        Returns a list of dicts with 'source_url' and 'title'.
        """
        # Select only necessary fields to reduce cost/bandwidth
        # Select only necessary fields to reduce cost/bandwidth
        docs = self.get_radar_items_collection(user_id, radar_id).select(["url", "title"]).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            results.append({
                "url": d.get("url"),
                "title": d.get("title")
            })
        return results

    # --- Exploration ---
    def get_exploration_collection(self, user_id: str):
        # Exploration data might be linked to 'sessions' but we can obtain metadata here
        return self._get_user_ref(user_id).collection("exploration")

    async def add_exploration_item(self, user_id: str, item_data: Dict[str, Any]):
        return await self.get_exploration_collection(user_id).add(item_data)

    async def get_exploration_items(self, user_id: str):
        docs = self.get_exploration_collection(user_id).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
        return results

    async def update_exploration_item(self, user_id: str, item_id: str, data: Dict[str, Any]):
        return await self.get_exploration_collection(user_id).document(item_id).update(data)

    async def delete_exploration_item(self, user_id: str, item_id: str):
        return await self.get_exploration_collection(user_id).document(item_id).delete()

    # --- Projects ---
    def get_projects_collection(self, user_id: str):
        return self._get_user_ref(user_id).collection("projects")

    async def add_project_item(self, user_id: str, item_data: Dict[str, Any]):
        return await self.get_projects_collection(user_id).add(item_data)

    async def get_project_items(self, user_id: str):
        docs = self.get_projects_collection(user_id).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
        return results

# Singleton instance
user_data_service = UserDataService()
