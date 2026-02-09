from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import uuid

class Feedback(BaseModel):
    """Represents feedback for a conversation."""
    score: int | float
    text: str | None = ""
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["deep-search"] = "deep-search"
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class ArxivConfig(BaseModel):
    categories: List[str] = []
    authors: List[str] = []
    keywords: List[str] = []
    keywordLogic: str = "OR" # "OR" (default) or "AND"
    journalReference: Optional[str] = None

class RadarCreate(BaseModel):
    title: str
    description: str
    sources: List[str]
    frequency: str
    outputMedia: str
    customPrompt: Optional[str] = ""
    arxivConfig: Optional[ArxivConfig] = None

class Radar(RadarCreate):
    id: str
    lastUpdated: str
    status: str
    latest_summary: Optional[str] = None

class RadarUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sources: Optional[List[str]] = None
    frequency: Optional[str] = None
    outputMedia: Optional[str] = None
    customPrompt: Optional[str] = None
    status: Optional[str] = None
    arxivConfig: Optional[ArxivConfig] = None

class ResearchRequest(BaseModel):
    query: str
    files: List[dict] = []
    sessionId: Optional[str] = None
    radarId: Optional[str] = None
    activeDocumentUrl: Optional[str] = None
    agent_type: Optional[str] = 'exploration'

class ResearchResponse(BaseModel):
    content: str
    files: List[dict] = []
    
class FileItem(BaseModel):
    path: str
    type: str
    name: str
