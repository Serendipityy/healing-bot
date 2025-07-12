"""
Chat components for handling user interactions and message display.
"""

import datetime
import os
from typing import Optional

import streamlit as st

from ..styles.main import get_loading_dots_html
from ..utils import get_api_client, format_conversation_title
from ragbase.config import Config
from shared import UIConstants


async def handle_chat_message(message: str, conversation_id: Optional[str] = None):
    """Handle chat message with streaming response"""
    api_client = get_api_client()
    
    # Display user message
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    # Add user message to session state
    st.session_state.messages.append({
        "role": "user", 
        "content": message,
        "timestamp": current_time
    })
    
    # Display user message
    with st.chat_message(
        "user",
        avatar=str(Config.Path.IMAGES_DIR / "user-avatar.jfif"),
    ):
        st.markdown(message)
    
    # Display assistant response
    assistant = st.chat_message(
        "assistant", 
        avatar=str(Config.Path.IMAGES_DIR / "bot-avatar-1.jpg")
    )
    
    with assistant:
        message_placeholder = st.empty()
        
        # Show loading animation
        message_placeholder.markdown(get_loading_dots_html(), unsafe_allow_html=True)
        
        full_response = ""
        sources = []
        response_started = False
        
        # Stream response from API
        for chunk in api_client.chat_stream(message, conversation_id):
            if chunk.get("type") == "token":
                content = chunk.get("content", "")
                full_response += content
                
                # Start showing response after meaningful content
                if not response_started and len(full_response.strip()) > 10:
                    response_started = True
                    message_placeholder.empty()
                
                # Update display
                if response_started:
                    message_placeholder.markdown(full_response + "▌")  # Cursor effect
            
            elif chunk.get("type") == "sources":
                sources = chunk.get("sources", [])
            
            elif chunk.get("type") == "error":
                error_msg = chunk.get("content", "Unknown error")
                message_placeholder.markdown(f"❌ {error_msg}")
                return None
            
            elif chunk.get("type") == "end":
                # Update conversation_id if it was created
                new_conversation_id = chunk.get("conversation_id")
                if new_conversation_id and not conversation_id:
                    st.session_state.current_conversation_id = new_conversation_id
                    conversation_id = new_conversation_id
                break
        
        # Final display without cursor
        if full_response:
            message_placeholder.markdown(full_response)
        
        # Show sources if available
        if sources:
            for i, source in enumerate(sources[:3]):
                with st.expander(f"Source #{i+1}", expanded=False):
                    content = source.get("content", "")
                    st.write(content)
    
    # Add assistant message to session state
    if full_response:
        st.session_state.messages.append({
            "role": "assistant", 
            "content": full_response,
            "timestamp": current_time
        })
    
    return conversation_id


def show_message_history():
    """Display message history"""
    for message in st.session_state.messages:
        role = message["role"]
        avatar_path = (
            Config.Path.IMAGES_DIR / "bot-avatar-1.jpg"
            if role == "assistant"
            else Config.Path.IMAGES_DIR / "user-avatar.jfif"
        )
        with st.chat_message(role, avatar=str(avatar_path)):
            st.markdown(message["content"])


def show_chat_input():
    """Display chat input and handle user messages"""
    if prompt := st.chat_input(UIConstants.CHAT_INPUT_PLACEHOLDER):
        # Check if conversation exists, create if not
        conversation_id = st.session_state.get("current_conversation_id")
        
        if not conversation_id:
            # Create new conversation
            api_client = get_api_client()
            result = api_client.create_conversation()
            if result:
                conversation_id = result["id"]
                st.session_state.current_conversation_id = conversation_id
                
                # Add initial assistant message
                current_time = datetime.datetime.now().strftime("%H:%M")
                initial_message = {
                    "role": "assistant",
                    "content": UIConstants.DEFAULT_GREETING,
                    "timestamp": current_time
                }
                st.session_state.messages = [initial_message]
        
        try:
            # Handle the message
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            new_conversation_id = loop.run_until_complete(
                handle_chat_message(prompt, conversation_id)
            )
            
            # Update conversation title if this is the first user message
            if new_conversation_id:
                user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
                if len(user_messages) == 1:
                    api_client = get_api_client()
                    title = format_conversation_title(prompt)
                    api_client.update_conversation_title(new_conversation_id, title)
                    
        except Exception as e:
            st.error(f"Error processing message: {str(e)}")
            
            # Add error message
            current_time = datetime.datetime.now().strftime("%H:%M")
            error_response = "Xin lỗi, mình đang gặp vấn đề kỹ thuật. Bạn có thể thử lại không?"
            
            with st.chat_message(
                "assistant", 
                avatar=str(Config.Path.IMAGES_DIR / "bot-avatar-1.jpg")
            ):
                st.markdown(error_response)
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": error_response,
                "timestamp": current_time
            })
