import asyncio
import random
import time
import datetime
import uuid

import streamlit as st
from dotenv import load_dotenv
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import LLMChainFilter

from ragbase.chain import ask_question, create_chain
from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.model import create_llm, create_reranker
from ragbase.retriever import create_hybrid_retriever
from ragbase.utils import load_documents_from_excel
from chat_storage import ChatStorage

import os
import base64

load_dotenv()

LOADING_MESSAGES = [
    "Please wait...",
]

# Initialize chat storage with SQLite
@st.cache_resource(show_spinner=False)
def get_chat_storage():
    db_path = "chat_history.db"
    return ChatStorage(db_file=db_path)

@st.cache_resource(show_spinner=False)
def build_qa_chain():
    # Load prebuilt vector store
    start = time.time()
    documents = load_documents_from_excel(excel_path=Config.Path.EXCEL_FILE)
    vector_store = Ingestor().ingest()  # No excel_path, loads existing vector store
    end = time.time()
    print(f"Thời gian embedding: {end - start} giây")
    
    llm = create_llm()
    # Apply Hybrid Retriever
    retriever = create_hybrid_retriever(llm, documents, vector_store)
    
    # Apply reranker (Contextual Compression Retriever)
    if Config.Retriever.USE_RERANKER:
        retriever = ContextualCompressionRetriever(
            base_compressor=create_reranker(), base_retriever=retriever
        )

    if Config.Retriever.USE_CHAIN_FILTER:
        retriever = ContextualCompressionRetriever(
            base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever
        )

    return create_chain(llm, retriever)

async def ask_chain(question: str, chain):
    full_response = ""
    assistant = st.chat_message(
        "assistant", avatar=str(Config.Path.IMAGES_DIR / "assistant-avatar.jfif")
    )
    with assistant:
        message_placeholder = st.empty()
        message_placeholder.status(random.choice(LOADING_MESSAGES), state="running")
        documents = []
        async for event in ask_question(chain, question, session_id="session-id-42"):
            if isinstance(event, str):
                full_response += event
                message_placeholder.markdown(full_response)
            if isinstance(event, list):
                documents.extend(event)
        # for i, doc in enumerate(documents):
        #     with st.expander(f"Source #{i+1}"):
        #         st.write(doc.page_content)

    # Save the message to history
    current_time = datetime.datetime.now().strftime("%H:%M")
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "timestamp": current_time
    })
    
    # Update and save the current conversation to history  
    # only save if there has been an actual conversation
    save_current_chat(is_real_conversation=True)

def save_current_chat(is_real_conversation=False):
    """
    Lưu cuộc trò chuyện hiện tại vào bộ nhớ lâu dài
    is_real_conversation: True nếu đã có tương tác thực từ người dùng
    """
    if "current_chat_id" not in st.session_state or not st.session_state.current_chat_id:
        # Create a new conversation if none exists
        chat_storage = get_chat_storage()
        chat_id = chat_storage.generate_chat_id()
        st.session_state.current_chat_id = chat_id
        
        # Find preview text from the first user message
        preview_text = "Cuộc hội thoại mới"
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                preview_text = msg["content"][:30] + "..." if len(msg["content"]) > 30 else msg["content"]
                break
        
        current_date = datetime.datetime.now().strftime("%d/%m/%Y")
        chat_data = {
            "id": chat_id,
            "preview": preview_text,
            "date": current_date,
            "messages": st.session_state.messages,
            "is_real_conversation": is_real_conversation
        }
    else:
        # Update the current conversation
        chat_storage = get_chat_storage()
        chat_id = st.session_state.current_chat_id
        chat_data = chat_storage.get_chat_by_id(chat_id)
        if chat_data:
            chat_data["messages"] = st.session_state.messages
            if is_real_conversation:
                chat_data["is_real_conversation"] = True
        else:
            preview_text = "Cuộc hội thoại mới"
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    preview_text = msg["content"][:30] + "..." if len(msg["content"]) > 30 else msg["content"]
                    break
            
            current_date = datetime.datetime.now().strftime("%d/%m/%Y")
            chat_data = {
                "id": chat_id,
                "preview": preview_text,
                "date": current_date,
                "messages": st.session_state.messages,
                "is_real_conversation": is_real_conversation
            }
    
    # Only save to persistent storage if there has been user interaction  
    # or if it has already been marked as a real conversation
    if is_real_conversation or chat_data.get("is_real_conversation", False):
        chat_storage = get_chat_storage()
        chat_storage.save_chat(chat_data)

def show_message_history():
    for message in st.session_state.messages:
        role = message["role"]
        avatar_path = (
            Config.Path.IMAGES_DIR / "assistant-avatar.jfif"
            if role == "assistant"
            else Config.Path.IMAGES_DIR / "user-avatar.jfif"
        )
        with st.chat_message(role, avatar=str(avatar_path)):
            st.markdown(message["content"])

def show_chat_input(chain):
    if prompt := st.chat_input("Hãy chia sẻ tâm sự của bạn..."):
        current_time = datetime.datetime.now().strftime("%H:%M")
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "timestamp": current_time
        })
        with st.chat_message(
            "user",
            avatar=str(Config.Path.IMAGES_DIR / "user-avatar.jfif"),
        ):
            st.markdown(prompt)
        asyncio.run(ask_chain(prompt, chain))

def load_chat_history(chat_id):
    """Tải một cuộc trò chuyện từ bộ nhớ lâu dài"""
    chat_storage = get_chat_storage()
    chat_data = chat_storage.get_chat_by_id(chat_id)
    
    if chat_data and "messages" in chat_data:
        st.session_state.messages = chat_data["messages"]
        st.session_state.current_chat_id = chat_id
        st.experimental_rerun()
    else:
        st.error("Không thể tải cuộc trò chuyện này")

def create_new_chat():
    """Tạo cuộc trò chuyện mới"""
    current_time = datetime.datetime.now().strftime("%H:%M")
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
            "timestamp": current_time
        }
    ]
    # Generate a new ID for the conversation
    chat_storage = get_chat_storage()
    chat_id = chat_storage.generate_chat_id()
    st.session_state.current_chat_id = chat_id
    
    st.experimental_rerun()

def delete_chat(chat_id):
    """Xóa một cuộc trò chuyện"""
    chat_storage = get_chat_storage()
    chat_storage.delete_chat(chat_id)
    
    if st.session_state.get("current_chat_id") == chat_id:
        create_new_chat()
    else:
        st.experimental_rerun()


def get_base64_of_image(image_path):
    """Chuyển đổi hình ảnh thành chuỗi base64"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string

def create_sidebar():
    with st.sidebar:
        if st.button("+ Cuộc trò chuyện mới", use_container_width=True, key="new_chat_btn"):
            create_new_chat()
        
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
        st.image(str(Config.Path.IMAGES_DIR / "sidebar-image-1.jpg"))
        
       
        st.markdown("### Lịch sử trò chuyện")
        
        chat_storage = get_chat_storage()
        all_chats = chat_storage.get_all_chats()
        
        real_chats = [chat for chat in all_chats if chat.get("is_real_conversation", False)]
        
        if real_chats:
            for chat in reversed(real_chats):
                with st.container():
                    col1, col2 = st.columns([3, 0.5])
                    with col1:
                        is_current = st.session_state.get("current_chat_id") == chat.get("id")
                        button_label = f"🔹 {chat['preview']}" if is_current else f"{chat['preview']}"
                        if st.button(button_label, key=f"btn_{chat['id']}", use_container_width=True):
                            load_chat_history(chat['id'])
                    with col2:
                        if st.button("🗑️", key=f"del_{chat['id']}", help="Xóa cuộc trò chuyện này"):
                            delete_chat(chat['id'])
        else:
            st.caption("Chưa có cuộc trò chuyện nào")

# Main app
st.set_page_config(
    page_title="Healing Bot", 
    page_icon="🤗",
    layout="wide"  
)

main_bg_path = str(Config.Path.IMAGES_DIR / "sidebar-bg-1.jpg")
if os.path.exists(main_bg_path):
    main_bg = get_base64_of_image(main_bg_path)
    st.markdown(f"""
        <style>
        div[data-testid="stAppViewContainer"] {{
            background-image: url("data:image/jpg;base64,{main_bg}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        .st-emotion-cache-1atd71m {{
            background-image: url("data:image/jpg;base64,{main_bg}");
        }}
        </style>
    """, unsafe_allow_html=True)
    
st.markdown("""
<style>
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Sidebar */
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
    
    /* Container */
    div[data-testid="stAppViewContainer"] {
        # background-color: white !important;
    }
    
    div[data-testid="stAppViewBlockContainer"] {
        padding: 0 4rem !important;
    }
    
    .main .block-container {
        # padding: 0 5rem;
        # margin-top: 5rem;
    }
    
    /* avatar */
    .st-emotion-cache-p4micv {
        width: 2.75rem;
        height: 2.75rem;
        border-radius: 50%;
    }
    
    .st-emotion-cache-1htpkgr {
        background-color: unset !important;
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
    
    .stChatInput {
        position: fixed !important;
        bottom: 0 !important;
        padding: 1rem !important;
        z-index: 999 !important;
        background-color: transparent !important;
    }
    
    .stChatInput > div {
        border: 1px solid #ddd;
    }
    
    button[data-testid="chatSubmitButton"] {
        border-radius: 50%;
    }
    
    .stButton button:hover {
        background-color: #f0f7ff !important;
    }
    
    .stButton button:first-of-type {
        background-color: #f0f7ff;
        border: 1px solid #ddd;
        font-weight: bold;
        # margin-bottom: 10px;
    }
    
    .stButton button {
        text-align: left;
        padding: 5px;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    button[data-testid="baseButton-secondary"]:has(div:contains("🔹")) {
        background-color: #e6f3ff !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    current_time = datetime.datetime.now().strftime("%H:%M")
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
            "timestamp": current_time
        }
    ]
    
    chat_storage = get_chat_storage()
    chat_id = chat_storage.generate_chat_id()
    st.session_state.current_chat_id = chat_id
    
create_sidebar()

chat_container = st.container()

with chat_container:
    with st.spinner("Starting..."):
        chain = build_qa_chain()
    
    show_message_history()

show_chat_input(chain)
