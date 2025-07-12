"""
Shared types and models between frontend and backend
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MessageData:
    role: str
    content: str
    timestamp: str
    conversation_id: Optional[str] = None


@dataclass
class ConversationData:
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageData]


@dataclass
class ChatStreamChunk:
    type: str  # "token" | "sources" | "error" | "end"
    content: str
    conversation_id: Optional[str] = None
    sources: List[dict] = None
