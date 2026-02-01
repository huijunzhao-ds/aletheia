from pydantic import BaseModel
from typing import List, Optional

class ArxivConfig(BaseModel):
    categories: List[str] = []
    authors: List[str] = []
    keywords: List[str] = []
    journalReference: Optional[str] = None

class RadarCreate(BaseModel):
    title: str
    description: str
    sources: List[str]
    frequency: str
    outputMedia: str
    isStarred: bool = False
    customPrompt: Optional[str] = ""
    arxivConfig: Optional[ArxivConfig] = None

class RadarItemResponse(RadarCreate):
    id: str
    lastUpdated: str
    status: str
    capturedCount: int = 0
    unreadCount: int = 0
    latest_summary: Optional[str] = None

class ResearchRequest(BaseModel):
    query: str
    files: List[dict] = []
    sessionId: Optional[str] = None
    radarId: Optional[str] = None

class ResearchResponse(BaseModel):
    content: str
    files: List[dict] = []
    
class FileItem(BaseModel):
    path: str
    type: str
    name: str
