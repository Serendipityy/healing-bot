"""
Shared types and constants between frontend and backend.
"""

from enum import Enum
from typing import Dict, Any

class MessageRole(str, Enum):
    """Message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class StreamChunkType(str, Enum):
    """Stream chunk types"""
    TOKEN = "token"
    SOURCES = "sources"
    ERROR = "error"
    END = "end"

class APIEndpoints:
    """API endpoint constants"""
    CHAT_STREAM = "/api/chat/stream"
    CHAT_MESSAGE = "/api/chat/message"
    CONVERSATIONS = "/api/conversations/"
    HEALTH = "/health"
    READY = "/ready"

class UIConstants:
    """UI related constants"""
    DEFAULT_GREETING = "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?"
    CHAT_INPUT_PLACEHOLDER = "Hãy chia sẻ tâm sự của bạn..."
    NEW_CONVERSATION_TITLE = "Cuộc trò chuyện mới"
    CONVERSATION_HISTORY_TITLE = "Lịch sử trò chuyện"
    
class Colors:
    """Color scheme constants"""
    PRIMARY = "#5BC099"
    BACKGROUND_USER = "#e6f3ff"
    BACKGROUND_ASSISTANT = "#f0f7ff"
    BACKGROUND_SIDEBAR = "#d7e6e4"
