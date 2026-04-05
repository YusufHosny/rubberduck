from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Project(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    resources: List["Resource"] = Relationship(
        back_populates="project", cascade_delete=True
    )
    chats: List["Chat"] = Relationship(back_populates="project", cascade_delete=True)


class Resource(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    project_id: str = Field(foreign_key="project.id")
    name: str
    type: str  # 'pdf', 'link', 'text'
    token_count: int = Field(default=0)
    file_path: Optional[str] = Field(default=None)  # relative to project/resources
    url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    project: Project = Relationship(back_populates="resources")


class Chat(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    project_id: str = Field(foreign_key="project.id")
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    project: Project = Relationship(back_populates="chats")
    messages: List["Message"] = Relationship(back_populates="chat", cascade_delete=True)


class Message(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    chat_id: str = Field(foreign_key="chat.id")
    role: str  # 'user', 'assistant', 'system', 'tool'
    type: str  # 'text', 'reasoning', 'tool_call', 'tool_result'
    content: str
    name: Optional[str] = Field(default=None)
    parent_id: Optional[str] = Field(default=None)
    tokens_used: int = Field(default=0)
    cost: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    chat: Chat = Relationship(back_populates="messages")
