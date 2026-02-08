import os
import logging
from fastapi import Header, HTTPException, Depends
import firebase_admin
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

# Initialize Firebase Admin
try:
    firebase_admin.get_app()
except ValueError:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VITE_FIREBASE_PROJECT_ID")
    if project_id:
        firebase_admin.initialize_app(options={'projectId': project_id})
    else:
        firebase_admin.initialize_app()

async def get_current_user(authorization: str = Header(None)):
    """
    Verifies the Firebase ID token sent from the frontend.
    """
    is_dev = os.getenv("ENV") == "development"
    
    if not authorization:
        if is_dev:
            logger.info("No auth header, using dev_user for local development")
            return "dev_user"
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Expect header in the form: "Bearer <token>"
        parts = authorization.strip().split(" ", 1)
        if len(parts) != 2 or not parts[1]:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            )
        scheme, token = parts[0], parts[1]
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization scheme. Expected 'Bearer'.",
            )
        # Verify the ID token using Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token.get("uid", "unknown_user")
    except HTTPException:
        # Re-raise HTTPExceptions unchanged
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        if is_dev:
            logger.warning("Token verification failed locally. Falling back to dev_user.")
            return "dev_user"
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
