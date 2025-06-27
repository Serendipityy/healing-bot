"""
Streamlit Frontend for Healing Bot
Clean frontend that communicates with FastAPI backend
"""
import base64
import datetime
import os
import requests
import streamlit as st
import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from frontend.api_client import APIClient
from frontend.ui_components import UIComponents
from ragbase.config import Config

# Initialize API client
@st.cache_resource
def get_api_client():
    return APIClient(base_url="http://localhost:8000")

# Initialize UI components
@st.cache_resource  
def get_ui_components():
    return UIComponents()

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        current_time = datetime.datetime.now().strftime("%H:%M")
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
                "timestamp": current_time
            }
        ]
        st.session_state.current_chat_id = None
        st.session_state.is_processing = False

def create_new_chat():
    """Create a new chat session"""
    try:
        api_client = get_api_client()
        response = api_client.create_chat()
        
        if response:
            current_time = datetime.datetime.now().strftime("%H:%M")
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
                    "timestamp": current_time
                }
            ]
            st.session_state.current_chat_id = response["chat_id"]
            st.rerun()
        else:
            st.error("Không thể tạo cuộc trò chuyện mới")
    except Exception as e:
        st.error(f"Lỗi khi tạo cuộc trò chuyện: {e}")

def load_chat_history(chat_id: str):
    """Load a specific chat history"""
    try:
        api_client = get_api_client()
        chat_data = api_client.get_chat_history(chat_id)
        
        if chat_data:
            st.session_state.messages = [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp", "")
                }
                for msg in chat_data["messages"]
            ]
            st.session_state.current_chat_id = chat_id
            st.rerun()
        else:
            st.error("Không thể tải cuộc trò chuyện này")
    except Exception as e:
        st.error(f"Lỗi khi tải lịch sử: {e}")

def delete_chat(chat_id: str):
    """Delete a chat session"""
    try:
        api_client = get_api_client()
        success = api_client.delete_chat(chat_id)
        
        if success:
            if st.session_state.get("current_chat_id") == chat_id:
                create_new_chat()
            else:
                st.rerun()
        else:
            st.error("Không thể xóa cuộc trò chuyện")
    except Exception as e:
        st.error(f"Lỗi khi xóa cuộc trò chuyện: {e}")

def show_message_history():
    """Display chat message history"""
    ui_components = get_ui_components()
    
    for message in st.session_state.messages:
        role = message["role"]
        avatar_path = ui_components.get_avatar_path(role)
        
        with st.chat_message(role, avatar=str(avatar_path)):
            st.markdown(message["content"])

def process_user_message(prompt: str):
    """Process user message and get response from backend"""
    if st.session_state.is_processing:
        return
    
    st.session_state.is_processing = True
    
    try:
        # Add user message to UI
        current_time = datetime.datetime.now().strftime("%H:%M")
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": current_time
        })
        
        # Display user message
        with st.chat_message("user", avatar=str(Config.Path.IMAGES_DIR / "user-avatar.jfif")):
            st.markdown(prompt)
        
        # Get or create chat session
        if not st.session_state.current_chat_id:
            api_client = get_api_client()
            response = api_client.create_chat(prompt)
            if response:
                st.session_state.current_chat_id = response["chat_id"]
        
        # Display assistant response
        with st.chat_message("assistant", avatar=str(Config.Path.IMAGES_DIR / "assistant-avatar.jfif")):
            message_placeholder = st.empty()
            message_placeholder.status("Đang suy nghĩ...", state="running")
            
            # Stream response from backend
            api_client = get_api_client()
            full_response = ""
            documents = []
            
            try:
                for chunk in api_client.send_message_stream(
                    chat_id=st.session_state.current_chat_id,
                    message=prompt,
                    chat_history=[
                        {"role": msg["role"], "content": msg["content"], "timestamp": msg.get("timestamp")}
                        for msg in st.session_state.messages[:-1]  # Exclude the current message
                    ]
                ):
                    if chunk.get("type") == "content":
                        full_response += chunk.get("content", "")
                        message_placeholder.markdown(full_response)
                    elif chunk.get("type") == "documents":
                        documents.extend(chunk.get("documents", []))
                    elif chunk.get("type") == "complete":
                        full_response = chunk.get("full_response", full_response)
                        break
                    elif chunk.get("type") == "error":
                        full_response = chunk.get("content", "Xin lỗi, đã có lỗi xảy ra.")
                        break
                
                # Display final response
                message_placeholder.markdown(full_response)
                
                # Show source documents
                for i, doc in enumerate(documents):
                    with st.expander(f"Nguồn #{i+1}"):
                        st.write(doc["content"])
                
                # Add assistant response to session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": current_time
                })
                
            except Exception as e:
                error_message = f"Xin lỗi, mình đang gặp vấn đề kỹ thuật: {str(e)}"
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "timestamp": current_time
                })
    
    except Exception as e:
        st.error(f"Lỗi xử lý tin nhắn: {e}")
    
    finally:
        st.session_state.is_processing = False

def show_chat_input():
    """Display chat input and handle user input"""
    if prompt := st.chat_input("Hãy chia sẻ tâm sự của bạn...", disabled=st.session_state.is_processing):
        process_user_message(prompt)

def create_sidebar():
    """Create sidebar with chat history"""
    ui_components = get_ui_components()
    
    with st.sidebar:
        if st.button("+ Cuộc trò chuyện mới", use_container_width=True, key="new_chat_btn"):
            create_new_chat()
        
        ui_components.apply_sidebar_styling()
        
        st.markdown("### Lịch sử trò chuyện")
        
        try:
            api_client = get_api_client()
            all_chats = api_client.get_all_chats()
            
            if all_chats:
                for chat in all_chats:
                    with st.container():
                        col1, col2 = st.columns([3, 0.5])
                        with col1:
                            is_current = st.session_state.get("current_chat_id") == chat["id"]
                            button_label = f"🔹 {chat['preview']}" if is_current else chat['preview']
                            if st.button(button_label, key=f"btn_{chat['id']}", use_container_width=True):
                                load_chat_history(chat['id'])
                        with col2:
                            if st.button("🗑️", key=f"del_{chat['id']}", help="Xóa cuộc trò chuyện này"):
                                delete_chat(chat['id'])
            else:
                st.caption("Chưa có cuộc trò chuyện nào")
        
        except Exception as e:
            st.error(f"Không thể tải lịch sử: {e}")

def main():
    """Main application"""
    # Page config
    st.set_page_config(
        page_title="Healing Bot",
        page_icon="🤗",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Apply styling
    ui_components = get_ui_components()
    ui_components.apply_main_styling()
    
    # Create sidebar
    create_sidebar()
    
    # Main chat interface
    chat_container = st.container()
    
    with chat_container:
        show_message_history()
    
    # Chat input
    show_chat_input()

if __name__ == "__main__":
    main()
