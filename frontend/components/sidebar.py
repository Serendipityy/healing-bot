"""
Sidebar UI components for conversation history and navigation.
"""

import datetime
import os

import streamlit as st

from ..utils import get_api_client, get_base64_of_image, format_conversation_title
from ragbase.config import Config
from shared import UIConstants


def create_sidebar():
    """Create and display the sidebar with conversation history"""
    with st.sidebar:
        # New conversation button
        if st.button(f"✚ {UIConstants.NEW_CONVERSATION_TITLE}", use_container_width=True, key="new_chat_btn"):
            create_new_conversation()
        
        # Set sidebar background
        sidebar_bg_path = str(Config.Path.IMAGES_DIR / "sidebar-bg-1.jpg") 
        if os.path.exists(sidebar_bg_path):
            sidebar_bg = get_base64_of_image(sidebar_bg_path)
            st.markdown(
                f"""
                <style>
                [data-testid="stSidebar"] {{
                    background-image: url("data:image/jpg;base64,{sidebar_bg}");
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
        
        # Sidebar image
        sidebar_image_path = str(Config.Path.IMAGES_DIR / "sidebar-image-1-new.jpg")
        if os.path.exists(sidebar_image_path):
            st.image(sidebar_image_path)
        
        st.markdown(f"### {UIConstants.CONVERSATION_HISTORY_TITLE}")
        
        # Load conversations from API
        api_client = get_api_client()
        all_conversations = api_client.get_conversations()
        
        if all_conversations:
            for conv in all_conversations:
                with st.container():
                    col1, col2 = st.columns([3, 0.5])
                    with col1:
                        is_current = st.session_state.get("current_conversation_id") == conv.get("id")
                        formatted_title = format_conversation_title(conv['title'])
                        button_label = f"🔹 {formatted_title}" if is_current else formatted_title
                        
                        if st.button(button_label, key=f"btn_{conv['id']}", use_container_width=True):
                            load_conversation(conv['id'])
                    
                    with col2:
                        if st.button("🗑️", key=f"del_{conv['id']}", help="Xóa cuộc trò chuyện này"):
                            delete_conversation(conv['id'])
        else:
            st.caption("Chưa có cuộc trò chuyện nào")


def load_conversation(conversation_id: str):
    """Load a conversation from API"""
    api_client = get_api_client()
    conversation = api_client.get_conversation(conversation_id)
    
    if conversation:
        # Convert API response to session state format
        messages = []
        for msg in conversation.get("messages", []):
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"]
            })
        
        st.session_state.messages = messages
        st.session_state.current_conversation_id = conversation_id
        st.rerun()
    else:
        st.error("Không thể tải cuộc trò chuyện này")


def create_new_conversation():
    """Create a new conversation"""
    api_client = get_api_client()
    result = api_client.create_conversation()
    
    if result:
        conversation_id = result["id"]
        current_time = datetime.datetime.now().strftime("%H:%M")
        
        initial_message = {
            "role": "assistant",
            "content": UIConstants.DEFAULT_GREETING,
            "timestamp": current_time
        }
        
        st.session_state.messages = [initial_message]
        st.session_state.current_conversation_id = conversation_id
        st.rerun()
    else:
        st.error("Không thể tạo cuộc trò chuyện mới")


def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    api_client = get_api_client()
    success = api_client.delete_conversation(conversation_id)
    
    if success:
        if st.session_state.get("current_conversation_id") == conversation_id:
            # Reset to no conversation state
            st.session_state.messages = []
            st.session_state.current_conversation_id = None
            st.rerun()
        else:
            st.rerun()
    else:
        st.error("Không thể xóa cuộc trò chuyện")
