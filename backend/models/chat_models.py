"""
Pydantic models for chat API
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    chat_history: Optional[List[ChatMessage]] = Field(None, description="Previous chat history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response")
    documents: Optional[List[Dict[str, Any]]] = Field(None, description="Retrieved documents")
    chat_id: str = Field(..., description="Chat session ID")

class ChatHistory(BaseModel):
    id: str = Field(..., description="Chat ID")
    preview: str = Field(..., description="Chat preview text")
    date: str = Field(..., description="Chat creation date")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    is_real_conversation: bool = Field(False, description="Whether this is a real conversation")

class CreateChatRequest(BaseModel):
    initial_message: Optional[str] = Field(None, description="Initial message for the chat")

class DeleteChatRequest(BaseModel):
    chat_id: str = Field(..., description="Chat ID to delete")
