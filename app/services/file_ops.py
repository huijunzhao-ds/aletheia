import os
import logging
from app.core.session_storage import get_storage_client
from app.core.config import BUCKET_NAME

logger = logging.getLogger(__name__)

def read_local_file(file_path: str) -> str:
    """
    Reads the text content of a local file saved in the system (e.g., from 'static/docs/').
    Supports PDF and text/markdown files.
    If the file is missing locally but exists in GCS backup, it will be restored.
    
    Args:
        file_path: The name or path of the file to read (e.g., 'static/docs/paper.pdf' or just 'paper.pdf').
        
    Returns:
        The text content of the file.
    """
    try:
        # Sanitize and resolve path
        # Check if full path or just filename
        if "static/docs/" in file_path:
            target_path = file_path.lstrip("/") # Remove leading slash if present
        else:
            target_path = os.path.join("static/docs", os.path.basename(file_path))
            
        # LAZY RESTORE FROM GCS if missing
        if not os.path.exists(target_path):
            try:
                # Try to restore from GCS (Cloud Run ephemeral storage fix)
                client = get_storage_client()
                if client:
                    bucket = client.bucket(BUCKET_NAME)
                    filename = os.path.basename(target_path)
                    blob_name = f"docs/{filename}"
                    blob = bucket.blob(blob_name)
                    
                    if blob.exists():
                        logger.info(f"Restoring missing file from GCS: {blob_name}")
                        # Ensure dir exists
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        blob.download_to_filename(target_path)
                    else:
                        logger.warning(f"File not found locally or in GCS: {blob_name}")
            except Exception as e:
                logger.warning(f"Failed to restore from GCS: {e}")

        if not os.path.exists(target_path):
            return f"Error: File not found at {target_path} (and restore failed)"
            
        # Security check: ensure path is within static/docs
        abs_target = os.path.abspath(target_path)
        abs_root = os.path.abspath("static/docs")
        if not abs_target.startswith(abs_root):
            return "Error: Access denied. Can only read files in static/docs/."
            
        file_ext = os.path.splitext(target_path)[1].lower()
        
        if file_ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(target_path)
                text = ""
                # Limit to first 20 pages to avoid context overflow for massive docs
                max_pages = 20
                for i, page in enumerate(reader.pages):
                    if i >= max_pages:
                        text += "\n[...Document Truncated...]"
                        break
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "Error: pypdf library not installed. Cannot read PDF."
            except Exception as e:
                return f"Error reading PDF: {e}"
        else:
            # Assume text/markdown
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Error reading local file {file_path}: {e}")
        return f"Failed to read file: {e}"
