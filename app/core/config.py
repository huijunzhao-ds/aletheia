import os

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOCS_DIR = os.path.join(STATIC_DIR, "docs")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
SLIDES_DIR = os.path.join(STATIC_DIR, "slides")
VIDEO_DIR = os.path.join(STATIC_DIR, "videos")

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

# GCS Bucket Name (if used)
# Prioritize explicit GCS bucket, then Firebase bucket, then auto-generated based on Project ID
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") or os.getenv("VITE_FIREBASE_STORAGE_BUCKET") or (f"{PROJECT_ID}-aletheia-docs" if PROJECT_ID else "local-aletheia-docs")
