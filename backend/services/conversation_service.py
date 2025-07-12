import datetime
import uuid
from typing import List, Optional

from chat_storage import ChatStorage
from ..models.chat import Conversation, Message, ConversationCreate


class ConversationService:
    def __init__(self, db_file: str = "chat_history.db"):
        self.storage = ChatStorage(db_file=db_file)
    
    def create_conversation(self, title: Optional[str] = None) -> str:
        """Create a new conversation and return its ID"""
        return self.storage.create_conversation(title)
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        # Get conversation info
        conversations = self.storage.get_all_conversations()
        conversation_data = next(
            (conv for conv in conversations if conv["id"] == conversation_id), 
            None
        )
        
        if not conversation_data:
            return None
        
        # Get messages
        messages = self.storage.get_conversation_messages(conversation_id)
        
        return Conversation(
            id=conversation_data["id"],
            title=conversation_data["title"],
            created_at=conversation_data["created_at"],
            updated_at=conversation_data["updated_at"],
            messages=[
                Message(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg["timestamp"],
                    conversation_id=conversation_id
                )
                for msg in messages
            ]
        )
    
    def get_all_conversations(self) -> List[dict]:
        """Get all conversations"""
        return self.storage.get_all_conversations()
    
    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        try:
            self.storage.update_conversation_title(conversation_id, title)
            return True
        except Exception:
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            self.storage.delete_conversation(conversation_id)
            return True
        except Exception:
            return False
    
    def save_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str, 
        timestamp: Optional[str] = None
    ) -> bool:
        """Save a message to conversation"""
        try:
            if not timestamp:
                timestamp = datetime.datetime.now().strftime("%H:%M")
            self.storage.save_message(conversation_id, role, content, timestamp)
            return True
        except Exception:
            return False
    
    def get_conversation_messages(self, conversation_id: str) -> List[dict]:
        """Get messages for a conversation"""
        return self.storage.get_conversation_messages(conversation_id)


# Global service instance
conversation_service = None

def get_conversation_service() -> ConversationService:
    """Get or create conversation service instance"""
    global conversation_service
    if conversation_service is None:
        conversation_service = ConversationService()
    return conversation_service
