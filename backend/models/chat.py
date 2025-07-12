from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class Message(BaseModel):
    id: Optional[str] = None
    role: str
    content: str
    timestamp: str
    conversation_id: str


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class Conversation(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Message] = []


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[dict] = []


class StreamChunk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    type: str  # "token" | "sources" | "error" | "end"
    content: str
    conversation_id: Optional[str] = None
    sources: List[dict] = []
