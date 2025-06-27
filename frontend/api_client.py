"""
API Client for communicating with FastAPI backend
"""
import requests
import json
from typing import Dict, List, Any, Optional, Generator
import time

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if backend is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def create_chat(self, initial_message: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Create a new chat session"""
        try:
            payload = {}
            if initial_message:
                payload["initial_message"] = initial_message
            
            response = self.session.post(
                f"{self.base_url}/chat/create",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating chat: {e}")
            return None
    
    def send_message_stream(
        self, 
        chat_id: str, 
        message: str, 
        chat_history: Optional[List[Dict]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Send message and stream response"""
        try:
            payload = {
                "message": message,
                "chat_history": chat_history or []
            }
            
            response = self.session.post(
                f"{self.base_url}/chat/{chat_id}/message",
                json=payload,
                stream=True,
                headers={"Accept": "text/plain"},
                timeout=60
            )
            response.raise_for_status()
            
            # Simple streaming without SSE parsing for now
            # We'll implement a simpler version
            full_response = ""
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # Simple content streaming
                    if line.startswith("data: "):
                        content = line[6:]  # Remove "data: " prefix
                        if content and content != "Response complete":
                            full_response += content
                            yield {
                                "type": "content",
                                "content": content
                            }
                    elif line.startswith("event: complete"):
                        yield {
                            "type": "complete",
                            "full_response": full_response
                        }
                        break
                    elif line.startswith("event: error"):
                        yield {
                            "type": "error",
                            "content": "Đã có lỗi xảy ra"
                        }
                        break
                        
        except Exception as e:
            print(f"Error streaming message: {e}")
            yield {
                "type": "error",
                "content": f"Lỗi kết nối: {str(e)}"
            }
    
    def get_chat_history(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat history for a specific chat"""
        try:
            response = self.session.get(
                f"{self.base_url}/chat/{chat_id}/history",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return None
    
    def get_all_chats(self) -> List[Dict[str, Any]]:
        """Get all chat sessions"""
        try:
            response = self.session.get(
                f"{self.base_url}/chats",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting all chats: {e}")
            return []
    
    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat session"""
        try:
            response = self.session.delete(
                f"{self.base_url}/chat/{chat_id}",
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error deleting chat: {e}")
            return False
