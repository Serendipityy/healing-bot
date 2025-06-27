"""
UI Components for Streamlit frontend
"""
import base64
import os
import streamlit as st
from pathlib import Path
from ragbase.config import Config

class UIComponents:
    def __init__(self):
        self.images_dir = Config.Path.IMAGES_DIR
    
    def get_avatar_path(self, role: str) -> Path:
        """Get avatar path for a role"""
        if role == "assistant":
            return self.images_dir / "assistant-avatar.jfif"
        else:
            return self.images_dir / "user-avatar.jfif"
    
    def get_base64_of_image(self, image_path: str) -> str:
        """Convert image to base64 string"""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            return encoded_string
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return ""
    
    def apply_sidebar_styling(self):
        """Apply styling to sidebar"""
        sidebar_bg_path = str(self.images_dir / "sidebar-bg-1.jpg")
        
        if os.path.exists(sidebar_bg_path):
            sidebar_bg = self.get_base64_of_image(sidebar_bg_path)
            if sidebar_bg:
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
        
        # Show sidebar image if exists
        sidebar_image_path = self.images_dir / "sidebar-image-1.jpg"
        if sidebar_image_path.exists():
            st.image(str(sidebar_image_path))
    
    def apply_main_styling(self):
        """Apply main styling to the app"""
        main_bg_path = str(self.images_dir / "sidebar-bg-1.jpg")
        main_bg = ""
        
        if os.path.exists(main_bg_path):
            main_bg = self.get_base64_of_image(main_bg_path)
        
        st.markdown(f"""
        <style>
            header[data-testid="stHeader"] {{
                display: none !important;
            }}
            
            /* Main background */
            div[data-testid="stAppViewContainer"] {{
                background-image: url("data:image/jpg;base64,{main_bg}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
            }}
            
            .st-emotion-cache-1atd71m {{
                background-image: url("data:image/jpg;base64,{main_bg}");
            }}
            
            /* Sidebar */
            section[data-testid="stSidebar"] {{
                width: 25% !important;
                padding: 1rem;
                box-shadow: 2px 0 5px rgba(0,0,0,0.1);
            }}
            
            div[data-testid="stSidebarHeader"] {{
                padding: 0 !important;
            }}
            
            button[data-testid="StyledFullScreenButton"] {{
                display: none;
            }}
            
            button[data-testid="baseButton-headerNoPadding"] {{
                color: black !important;
            }}
            
            /* Main container */
            div[data-testid="stMainBlockContainer"] {{
                padding: 0 4rem !important;
            }}
            
            /* Avatar styling */
            .st-emotion-cache-p4micv {{
                width: 2.75rem;
                height: 2.75rem;
                border-radius: 50%;
            }}
            
            .st-emotion-cache-1htpkgr {{
                background-color: unset !important;
            }}
            
            div[data-testid*="stChatMessage"] {{
                align-items: center !important;
            }}
            
            div[data-testid*="stChatMessageContent"] {{
                padding: 0 !important;
            }}
            
            .st-emotion-cache-1gwvy71 {{
                padding: 0;
            }}
            
            div[data-testid*="stChatMessageContent user"] {{
                background-color: #e6f3ff;
            }}
            
            div[data-testid*="stChatMessageContent assistant"] {{
                background-color: #f0f7ff;
            }}
            
            div[data-testid="stMarkdownContainer"] {{
                color: black !important;
            }}
           
            h1, h3 {{
                color: black !important;
            }} 
            
            .st-emotion-cache-1lm6gnd {{
                display: none !important;
            }}
            
            .st-emotion-cache-hu32sh {{
                background: unset !important;
            }}
            
            button[data-testid="chatSubmitButton"] {{
                border-radius: 50%;
            }}
            
            .st-emotion-cache-1f3w014 {{
                fill: #5BC099;
            }}
            
            button[data-testid="stChatInputSubmitButton"]:hover {{
                background: unset !important;
            }}
            
            .stButton button:hover {{
                background-color: #f0f7ff !important;
            }}
            
            .stChatInput > div,
            .st-b1 {{
                background: white !important;
            }}
            
            textarea {{
                color: black !important;
                caret-color: black !important;
                background: white !important;
            }}
            
            .stButton button:first-of-type {{
                background-color: #f0f7ff;
                border: 1px solid #ddd;
                font-weight: bold;
            }}
            
            .stButton button {{
                text-align: left;
                padding: 5px;
                margin-bottom: 5px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            button[data-testid="baseButton-secondary"]:has(div:contains("🔹")) {{
                background-color: #e6f3ff !important;
                font-weight: bold;
            }}
        </style>
        """, unsafe_allow_html=True)
