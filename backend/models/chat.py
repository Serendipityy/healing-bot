"""
Pydantic models for chat functionality.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Model for creating a new message."""
    content: str = Field(..., description="Message content")
    role: str = Field(default="user", description="Message role (user/assistant)")


class Message(BaseModel):
    """Model for a chat message."""
    id: Optional[str] = Field(None, description="Message ID")
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")
    conversation_id: str = Field(..., description="Conversation ID")


class ConversationCreate(BaseModel):
    """Model for creating a new conversation."""
    title: Optional[str] = Field("New Conversation", description="Conversation title")


class Conversation(BaseModel):
    """Model for a conversation with messages."""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    messages: List[Message] = Field(default=[], description="List of messages")


class ChatRequest(BaseModel):
    """Model for a chat request."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    session_id: Optional[str] = Field(None, description="Session ID")


class ChatResponse(BaseModel):
    """Model for a chat response."""
    response: str = Field(..., description="AI response")
    conversation_id: str = Field(..., description="Conversation ID")
    sources: List[dict] = Field(default=[], description="Source documents")


class StreamChunk(BaseModel):
    """Model for streaming response chunks."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    type: str = Field(..., description="Chunk type: token/sources/error/end")
    content: str = Field(..., description="Chunk content")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    sources: List[dict] = Field(default=[], description="Source documents")
