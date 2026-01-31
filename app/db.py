import os
import logging
from typing import Optional, Any, Dict, List
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
            
            key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gcp-sa-key.json")
            if os.path.exists(key_path):
                self.db = firestore.AsyncClient(database=database_id, project=project_id, credentials=None) # credentials=None will check GOOGLE_APPLICATION_CREDENTIALS
                # Actually, better to use from_service_account_json
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
        
    # --- Research Radar ---
    def get_radar_collection(self, user_id: str):
        return self._get_user_ref(user_id).collection("radar")

    async def add_radar_item(self, user_id: str, item_data: Dict[str, Any]):
        return await self.get_radar_collection(user_id).add(item_data)

    async def get_radar_items(self, user_id: str):
        docs = self.get_radar_collection(user_id).stream()
        return [doc.to_dict() async for doc in docs]

    async def update_radar_item(self, user_id: str, radar_id: str, item_data: Dict[str, Any]):
        return await self.get_radar_collection(user_id).document(radar_id).update(item_data)

    async def delete_radar_item(self, user_id: str, radar_id: str):
        return await self.get_radar_collection(user_id).document(radar_id).delete()

    # --- Exploration ---
    def get_exploration_collection(self, user_id: str):
        # Exploration data might be linked to 'sessions' but we can obtain metadata here
        return self._get_user_ref(user_id).collection("exploration")

    async def add_exploration_item(self, user_id: str, item_data: Dict[str, Any]):
        return await self.get_exploration_collection(user_id).add(item_data)

    async def get_exploration_items(self, user_id: str):
        docs = self.get_exploration_collection(user_id).stream()
        return [doc.to_dict() async for doc in docs]

    # --- Projects ---
    def get_projects_collection(self, user_id: str):
        return self._get_user_ref(user_id).collection("projects")

    async def add_project_item(self, user_id: str, item_data: Dict[str, Any]):
        return await self.get_projects_collection(user_id).add(item_data)

    async def get_project_items(self, user_id: str):
        docs = self.get_projects_collection(user_id).stream()
        return [doc.to_dict() async for doc in docs]

# Singleton instance
user_data_service = UserDataService()
