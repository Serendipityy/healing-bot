import sys
import os

# Add the parent directory to sys.path to import from ragbase
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time

from frontend.components.chat import show_message_history, show_chat_input
from frontend.components.sidebar import create_sidebar
from frontend.styles.main import get_all_styles
from frontend.utils.api_client import set_background_image, get_api_client
from ragbase.config import Config


def check_backend_status():
    """Check if backend is ready and show loading if not"""
    api_client = get_api_client()
    
    # Check if backend is accessible
    try:
        health = api_client.get_health_status()
        ready = api_client.check_backend_ready()
        
        if ready.get("status") != "ready":
            st.warning("🔄 Backend is starting up, models are loading...")
            
            # Show loading progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(30):  # Max 30 seconds wait
                ready = api_client.check_backend_ready()
                if ready.get("status") == "ready":
                    progress_bar.progress(100)
                    status_text.success("✅ All models loaded successfully!")
                    time.sleep(1)
                    st.experimental_rerun()
                    return True
                
                progress = min(95, (i + 1) * 3)  # Progress up to 95%
                progress_bar.progress(progress)
                status_text.info(f"⏳ Loading models... {progress}%")
                time.sleep(1)
            
            st.error("❌ Backend took too long to start. Please check the backend service.")
            return False
        
        return True
        
    except Exception as e:
        st.error(f"❌ Cannot connect to backend: {str(e)}")
        st.info("Please ensure the backend is running at http://localhost:8000")
        return False


def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None


def setup_page_config():
    """Setup Streamlit page configuration"""
    st.set_page_config(
        page_title="Healing Bot", 
        page_icon="🤗",
        layout="wide"  
    )


def apply_styles():
    """Apply CSS styles to the app"""
    # Apply main styles
    st.markdown(get_all_styles(), unsafe_allow_html=True)
    
    # Set background images
    main_bg_path = str(Config.Path.IMAGES_DIR / "sidebar-bg-1.jpg")
    main_bg_css = set_background_image(main_bg_path, "main")
    if main_bg_css:
        st.markdown(main_bg_css, unsafe_allow_html=True)


def main():
    """Main application function"""
    # Setup page
    setup_page_config()
    initialize_session_state()
    apply_styles()
    
    # Check backend status first
    if not check_backend_status():
        st.stop()  # Stop execution if backend not ready
    
    # Create sidebar
    create_sidebar()
    
    # Main chat container
    chat_container = st.container()
    
    with chat_container:
        # Show message history if conversation exists
        if st.session_state.get("current_conversation_id") is not None and st.session_state.messages:
            show_message_history()
        else:
            # Show default greeting
            with st.chat_message(
                "assistant", 
                avatar=str(Config.Path.IMAGES_DIR / "bot-avatar-1.jpg")
            ):
                st.markdown("Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?")
    
    # Chat input
    show_chat_input()


if __name__ == "__main__":
    main()
