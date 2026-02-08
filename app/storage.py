
import os
import logging
from google.cloud import storage
import datetime

logger = logging.getLogger(__name__)

# Fallback bucket name if not configured
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") or (f"{PROJECT_ID}-aletheia-docs" if PROJECT_ID else "local-aletheia-docs")

storage_client = None

def get_storage_client():
    global storage_client
    if storage_client is None:
        try:
            storage_client = storage.Client()
        except Exception as e:
            logger.warning(f"Could not initialize GCS client: {e}. Usage will fall back to local disk.")
            storage_client = False # Sentinel for failure
    return storage_client

def upload_to_gcs(file_bytes: bytes, destination_blob_name: str, content_type: str = "application/pdf") -> str:
    """
    Uploads a file to Google Cloud Storage and returns the public URL.
    """
    client = get_storage_client()
    
    if not client or not PROJECT_ID:
        logger.info("GCS not available or PROJECT_ID not set. Skipping cloud upload.")
        return None

    try:
        bucket = client.bucket(BUCKET_NAME)
        # Check if bucket exists, if not try to create (might fail on permissions)
        if not bucket.exists():
            try:
                logger.info(f"Bucket {BUCKET_NAME} not found, attempting to create...")
                bucket.create(location="US")
            except Exception as e:
                logger.error(f"Failed to create bucket {BUCKET_NAME}: {e}")
                return None

        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(file_bytes, content_type=content_type)
        
        logger.info(f"File uploaded to gs://{BUCKET_NAME}/{destination_blob_name}")
        
        # Determine accessible URL. 
        # Ideally we'd use signed URLs, but for this MVP we might rely on the authenticated user 
        # accessing it via a proxy or if the bucket is public.
        # For now, let's return the storage API link which works if the user is authenticated with Google? 
        # No, that won't work for the frontend directly without a proxy.
        
        # Let's return the gs:// URI and handle serving in the backend proxy if needed.
        # BUT, standard practice for simple apps: make it public or use Signed URLs.
        # Let's try to make it public logic:
        # blob.make_public()
        # return blob.public_url
        
        # Since I can't guarantee permissions to make public, I'll return a special prefix
        # that the backend can recognize to proxy or sign.
        return f"gs://{BUCKET_NAME}/{destination_blob_name}"

    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")
        return None

def generate_signed_url(gcs_uri: str, expiration=3600) -> str:
    """
    Generates a signed URL for a GS URI.
    """
    if not gcs_uri.startswith("gs://"):
        return None
    
    try:
        client = get_storage_client()
        if not client: return None
        
        # Parse gs://bucket/blob
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        if len(parts) != 2: return None
        
        bucket_name, blob_name = parts
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        return blob.generate_signed_url(expiration=datetime.timedelta(seconds=expiration), method="GET")
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        return None
