from pydantic import BaseModel
from typing import List, Optional

class UploadedFile(BaseModel):
    name: str
    mime_type: str
    data: str  # Base64 encoded data

class ResearchRequest(BaseModel):
    query: str
    sessionId: Optional[str] = None
    files: List[UploadedFile] = []

class FileItem(BaseModel):
    path: str
    type: str  # 'audio', 'video', 'presentation'
    name: str

class ResearchResponse(BaseModel):
    content: str
    files: List[FileItem]
