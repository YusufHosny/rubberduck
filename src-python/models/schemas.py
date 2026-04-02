from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str


class ResourceCreate(BaseModel):
    name: str
    url: Optional[str] = None
    type: str  # pdf, link, text
    content: Optional[str] = None  # For text resource


class ChatCreate(BaseModel):
    name: str


class MessageCreate(BaseModel):
    role: str
    content: str
    parent_id: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    parent_id: Optional[str]
    created_at: datetime
