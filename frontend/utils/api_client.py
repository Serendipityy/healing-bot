import base64
import json
import os
from typing import Dict, List, Optional

import requests
import streamlit as st


class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def _make_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return None
    
    def check_backend_ready(self) -> dict:
        """Check if backend is ready"""
        response = self._make_request("GET", "/ready")
        return response.json() if response else {"status": "error"}
    
    def get_health_status(self) -> dict:
        """Get health status"""
        response = self._make_request("GET", "/health")
        return response.json() if response else {"status": "error"}
    
    def create_conversation(self, title: Optional[str] = None) -> Optional[Dict]:
        """Create a new conversation"""
        payload = {"title": title} if title else {}
        response = self._make_request("POST", "/api/conversations/", json=payload)
        return response.json() if response else None
    
    def get_conversations(self) -> List[Dict]:
        """Get all conversations"""
        response = self._make_request("GET", "/api/conversations/")
        return response.json() if response else []
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a specific conversation"""
        response = self._make_request("GET", f"/api/conversations/{conversation_id}")
        return response.json() if response else None
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        response = self._make_request("DELETE", f"/api/conversations/{conversation_id}")
        return response is not None
    
    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        response = self._make_request(
            "PUT", 
            f"/api/conversations/{conversation_id}/title",
            params={"title": title}
        )
        return response is not None
    
    def chat_stream(self, message: str, conversation_id: Optional[str] = None):
        """Stream chat response"""
        url = f"{self.base_url}/api/chat/stream"
        payload = {
            "message": message,
            "conversation_id": conversation_id
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                stream=True,
                headers={"Accept": "text/plain"}
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
        except requests.RequestException as e:
            st.error(f"Streaming Error: {str(e)}")
            yield {"type": "error", "content": str(e)}
    
    def chat_message(self, message: str, conversation_id: Optional[str] = None) -> Optional[Dict]:
        """Send chat message (non-streaming)"""
        payload = {
            "message": message,
            "conversation_id": conversation_id
        }
        response = self._make_request("POST", "/api/chat/message", json=payload)
        return response.json() if response else None


@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance"""
    return APIClient()


def get_base64_of_image(image_path: str) -> str:
    """Convert image to base64 string"""
    if not os.path.exists(image_path):
        return ""
    
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return encoded_string
    except Exception:
        return ""


def format_conversation_title(text: str, max_length: int = 30) -> str:
    """Format conversation title with max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def set_background_image(image_path: str, target: str = "main") -> str:
    """Set background image for app components"""
    base64_image = get_base64_of_image(image_path)
    if not base64_image:
        return ""
    
    if target == "main":
        return f"""
        <style>
        div[data-testid="stAppViewContainer"] {{
            background-image: url("data:image/jpg;base64,{base64_image}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        .st-emotion-cache-1atd71m {{
            background-image: url("data:image/jpg;base64,{base64_image}");
        }}
        </style>
        """
    elif target == "sidebar":
        return f"""
        <style>
        [data-testid="stSidebar"] {{
            background-image: url("data:image/jpg;base64,{base64_image}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        </style>
        """
    
    return ""
