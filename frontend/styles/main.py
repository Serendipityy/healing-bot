"""
CSS styles for the Healing Bot Streamlit frontend
"""

MAIN_CSS = """
<style>
    /* Hide default Streamlit elements */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Main container */
    div[data-testid="stAppViewContainer"] {
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }
    
    div[data-testid="stMainBlockContainer"] {
        padding: 0 4rem !important;
        height: calc(100vh - 120px) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        display: flex !important;
        flex-direction: column !important;
        scrollbar-width: thin !important;
        scrollbar-color: rgba(91, 192, 153, 0.7) rgba(91, 192, 153, 0.1) !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        width: 25% !important;
        padding: 1rem;
        box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }
    
    div[data-testid="stSidebarHeader"] {
        padding: 0 !important;
    }
    
    button[data-testid="StyledFullScreenButton"] {
        display: none;
    }
    
    button[data-testid="baseButton-headerNoPadding"] {
        color: black !important;
    }
    
    /* Chat message styling */
    .st-emotion-cache-p4micv {
        width: 2.75rem;
        height: 2.75rem;
        border-radius: 50%;
    }
    
    .st-emotion-cache-1htpkgr {
        background-color: unset !important;
    }
    
    .st-emotion-cache-janbn0 {
        background-color: #d7e6e4 !important;
    }
    
    div[data-testid*="stChatMessage"] {
        align-items: center !important;
    }
    
    div[data-testid*="stChatMessageContent"] {
        padding: 0 !important;
    }
    
    .st-emotion-cache-1gwvy71 {
        padding: 0;
    }
    
    div[data-testid*="stChatMessageContent user"] {
        background-color: #e6f3ff;
    }
    
    div[data-testid*="stChatMessageContent assistant"] {
        background-color: #f0f7ff;
    }
    
    div[data-testid="stMarkdownContainer"] {
        color: black !important;
    }
   
    h1, h3 {
        color: black !important;
    }
    
    /* Hide elements */
    .st-emotion-cache-1lm6gnd {
        display: none !important;
    }
    
    .st-emotion-cache-hu32sh {
        background: unset !important;
    }
</style>
"""

CHAT_INPUT_CSS = """
<style>
    /* Chat input styling */
    button[data-testid="chatSubmitButton"] {
        border-radius: 50%;
        position: relative !important;
        bottom: 0.5rem !important;
        flex-shrink: 0 !important;
        align-self: flex-end !important;
    }
    
    .st-emotion-cache-1f3w014 {
        fill: #5BC099;
    }
    
    button[data-testid="stChatInputSubmitButton"] .st-emotion-cache-1f3w014 {
        fill: white;  
    }
    
    button[data-testid="stChatInputSubmitButton"] {
        background-color: #5BC099 !important;
        border-radius: 50% !important;
        border: none !important;
        padding: 0.5rem;
        transform: translate(-0.5rem, 0);
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .stChatInput > div:first-child {
        background: white !important;
        height: 3.5rem !important;
        min-height: 3.5rem !important;
        max-height: 3.5rem !important;
        display: flex !important;
        align-items: center !important;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        transition: background-color 0.3s ease, box-shadow 0.3s ease; 
        border: 2px solid #5BC099 !important;
    }
    
    .stChatInput > div:first-child:hover,
    .stChatInput > div:first-child:focus-within {
        box-shadow: 0px 0px 8px rgba(91, 192, 153, 0.5); 
    }
    
    .st-bq {
        padding-right: 0;
        flex-grow: 1;
    }
    
    .st-emotion-cache-sey4o0 {
        align-items: center !important;
        height: 3.5rem !important;
        position: unset;
    }
    
    textarea {
        color: black !important;
        background: white !important;
        caret-color: black !important;
        resize: none !important;
        height: 2.5rem !important;
        min-height: 2.5rem !important;
        max-height: 2.5rem !important;
        overflow-y: auto !important;
    }
    
    div[data-testid="stBottomBlockContainer"] {
        position: sticky !important;
        bottom: 0 !important;
        background: inherit !important;
        z-index: 10 !important;
        border-top: 1px solid rgba(0,0,0,0.05) !important;
        padding: 2rem 4rem !important;
        padding-top: 1rem !important;
    }
</style>
"""

BUTTON_CSS = """
<style>
    /* Button styling */
    .stButton button:hover {
        background-color: #f0f7ff !important;
    }
    
    .stButton button:first-of-type {
        background-color: #f0f7ff;
        border: 1px solid #ddd;
        font-weight: bold;
    }
    
    .stButton button {
        text-align: center;
        padding: 8px 12px;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        word-break: break-word;
    }
</style>
"""

SCROLLBAR_CSS = """
<style>
    /* Custom scrollbar styling */
    div[data-testid="stMainBlockContainer"]::-webkit-scrollbar {
        width: 10px;
    }
    
    div[data-testid="stMainBlockContainer"]::-webkit-scrollbar-track {
        background: rgba(91, 192, 153, 0.1);
        border-radius: 5px;
        margin: 2px;
    }
    
    div[data-testid="stMainBlockContainer"]::-webkit-scrollbar-thumb {
        background: rgba(91, 192, 153, 0.7);
        border-radius: 5px;
        border: 1px solid rgba(91, 192, 153, 0.3);
    }
    
    div[data-testid="stMainBlockContainer"]::-webkit-scrollbar-thumb:hover {
        background: rgba(91, 192, 153, 0.9);
        border: 1px solid rgba(91, 192, 153, 0.5);
    }
    
    div[data-testid="stMainBlockContainer"]::-webkit-scrollbar-thumb:active {
        background: #5BC099;
    }
    
    .main::-webkit-scrollbar {
        width: 10px;
    }
    
    .main::-webkit-scrollbar-track {
        background: rgba(91, 192, 153, 0.1);
        border-radius: 5px;
    }
    
    .main::-webkit-scrollbar-thumb {
        background: rgba(91, 192, 153, 0.7);
        border-radius: 5px;
        border: 1px solid rgba(91, 192, 153, 0.3);
    }
    
    .main::-webkit-scrollbar-thumb:hover {
        background: rgba(91, 192, 153, 0.9);
    }
    
    div[data-testid="stMainBlockContainer"] {
        scrollbar-gutter: stable !important;
    }
    
    div[data-testid="stMainBlockContainer"]::-webkit-scrollbar-thumb {
        transition: background-color 0.2s ease !important;
    }
    
    div[data-testid="stMainBlockContainer"]:hover::-webkit-scrollbar-thumb {
        background: rgba(91, 192, 153, 0.8) !important;
    }
</style>
"""

LOADING_ANIMATION_CSS = """
<style>
    .loading-dots {
        display: inline-flex;
        align-items: center;
    }
    
    .dot {
        width: 4px;
        height: 4px;
        margin: 0 2px;
        background-color: #5BC099;
        border-radius: 50%;
        animation: loading 1.4s infinite ease-in-out;
    }
    
    .dot:nth-child(1) { animation-delay: -0.32s; }
    .dot:nth-child(2) { animation-delay: -0.16s; }
    .dot:nth-child(3) { animation-delay: 0s; }
    
    @keyframes loading {
        0%, 80%, 100% {
            transform: scale(0);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
</style>
"""

TOOLTIP_CSS = """
<style>
    .stTooltipContent {
        background-color: #effbf6 !important;
        color: white !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        padding: 8px 12px !important;
    }
</style>
"""

def get_all_styles():
    """Get all CSS styles combined"""
    return MAIN_CSS + CHAT_INPUT_CSS + BUTTON_CSS + SCROLLBAR_CSS + LOADING_ANIMATION_CSS + TOOLTIP_CSS

def get_loading_dots_html():
    """Get loading dots HTML"""
    return """
    <div style="display: flex; align-items: center; padding: 10px;">
        <div class="loading-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    </div>
    """ + LOADING_ANIMATION_CSS
