import asyncio
import base64
import datetime
import os
import random
import re
import time
import uuid

import grpc.experimental.aio as grpc_aio
import nest_asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import \
    LLMChainFilter
from langchain_qdrant import Qdrant, QdrantVectorStore
from qdrant_client import QdrantClient

from chat_storage import ChatStorage
from ragbase.chain import ask_question, create_chain
from ragbase.config import Config
from ragbase.hyde import QueryTransformationHyDE
from ragbase.ingestor import Ingestor
from ragbase.model import create_embeddings, create_llm, create_reranker
from ragbase.retriever import create_hybrid_retriever, create_optimized_retriever
from ragbase.session_history import get_session_history, add_message_to_history, load_history_from_db
from ragbase.utils import (load_documents_from_excel,
                           load_summary_documents_from_excel)

# grpc_aio.init_grpc_aio()
load_dotenv()

LOADING_MESSAGES = [
    "Please wait...",
]

client = QdrantClient(host="localhost", port=6333, timeout=300)

# Initialize chat storage with SQLite
@st.cache_resource(show_spinner=False)
def get_chat_storage():
    db_path = "chat_history.db"
    return ChatStorage(db_file=db_path)

# Cache HyDE instance to avoid re-creating it
@st.cache_resource(show_spinner=False)
def get_hyde_transformer():
    return QueryTransformationHyDE()

# Cache embedding model to avoid reloading
@st.cache_resource(show_spinner=False)
def get_embedding_model():
    return create_embeddings()


@st.cache_resource(show_spinner=False)
def build_qa_chain():
    start = time.time()
    
    embedding_model = get_embedding_model()  # Use cached embedding model
    
    # Load collection "documents" - NO EXCEL LOADING NEEDED!
    vector_store = QdrantVectorStore(
        client=client,
        collection_name="documents", 
        embedding=embedding_model
    )

    # Load collection "summary" - NO EXCEL LOADING NEEDED!
    summary_vector_store = QdrantVectorStore(
        client=client,
        collection_name="summary",
        embedding=embedding_model
    )
    
    llm = create_llm()

    # Create optimized retrievers without loading Excel files
    retriever_full = create_optimized_retriever(llm, vector_store, "full")
    retriever_summary = create_optimized_retriever(llm, summary_vector_store, "summary")

    # Apply reranker or chain filter if needed
    if Config.Retriever.USE_RERANKER:
        retriever_full = ContextualCompressionRetriever(
            base_compressor=create_reranker(), base_retriever=retriever_full
        )
        retriever_summary = ContextualCompressionRetriever(
            base_compressor=create_reranker(), base_retriever=retriever_summary
        )

    if Config.Retriever.USE_CHAIN_FILTER:
        retriever_full = ContextualCompressionRetriever(
            base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_full
        )
        retriever_summary = ContextualCompressionRetriever(
            base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_summary
        )

    end = time.time()
    print(f"⚡ Chain initialized in: {end - start:.2f} seconds")
    
    return create_chain(llm, retriever_full, retriever_summary)

# Utility function to run async functions in Streamlit
@st.cache_resource
def get_async_loop():
    try:
        # Check if there's a running loop first
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except Exception as e:
        # Fall back to a new loop if any issues
        st.warning(f"Event loop error (handled): {e}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

def run_async_in_streamlit(async_func, *args, **kwargs):
    # Create a future in the current event loop
    loop = get_async_loop()
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))
    except RuntimeError as e:
        if "This event loop is already running" in str(e):
            # We're in a running event loop already, create a new task
            st.warning("Already in an event loop, creating a task instead")
            return asyncio.create_task(async_func(*args, **kwargs))
        else:
            raise

async def ask_chain(question: str, chain):
    assistant = st.chat_message(
        "assistant", avatar=str(Config.Path.IMAGES_DIR / "assistant-avatar.jfif")
    )
    with assistant:
        message_placeholder = st.empty()
        message_placeholder.status("🤔 Đang suy nghĩ...", state="running")
        
        full_response = ""
        documents = []
        
        # Start timing
        start_time = time.time()
        
        original_question = question
        
        # HyDE transformation with timing (with fast mode for simple queries)
        hyde_start = time.time()
        hyde_transformer = get_hyde_transformer()
        question_transformed = hyde_transformer.transform_query(original_question, fast_mode=True)
        hyde_end = time.time()
        print(f"⚡ HyDE took: {hyde_end - hyde_start:.2f}s")
        
        # Sử dụng conversation_id từ session state
        conversation_id = st.session_state.get("current_conversation_id", "default")
        
        # Update status based on process
        if hyde_end - hyde_start < 0.5:
            message_placeholder.status("🔍 Đang tìm kiếm thông tin...", state="running")
        else:
            message_placeholder.status("🧠 Đang phân tích câu hỏi...", state="running")
            time.sleep(0.5)  # Brief pause to show status
            message_placeholder.status("🔍 Đang tìm kiếm thông tin...", state="running")
        
        # Stream response with improved display
        chunk_count = 0
        response_started = False
        
        async for event in ask_question(chain, question_transformed, session_id=conversation_id):
            if isinstance(event, str) and event.strip():
                chunk_count += 1
                full_response += event
                
                # Start showing response after first meaningful chunk
                if not response_started and len(full_response.strip()) > 10:
                    response_started = True
                    message_placeholder.empty()
                
                # Update display every few chunks or when we have substantial content
                if response_started and (chunk_count % 3 == 0 or len(event) > 20):
                    # Remove thinking tags before displaying
                    display_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
                    message_placeholder.markdown(display_response + "▌")  # Cursor effect
                    
            if isinstance(event, list):
                documents.extend(event)

        # Final cleanup and display
        end_time = time.time()
        total_time = end_time - start_time
        
        # Remove thinking tags from final response
        full_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
        
        # Final display without cursor
        message_placeholder.markdown(full_response)
        
        print(f"🏁 Total response time: {total_time:.2f}s")
        
        # Show sources
        if documents:
            for i, doc in enumerate(documents[:3]):  # Limit to top 3 sources
                with st.expander(f"Source #{i+1}", expanded=False):
                    st.write(doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content)

    # Save to session and database
    current_time = datetime.datetime.now().strftime("%H:%M")
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "timestamp": current_time
    })
    
    add_message_to_history(conversation_id, "assistant", full_response)


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
        
        # Lưu tin nhắn user vào UI
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "timestamp": current_time
        })
        
        # Hiển thị tin nhắn user
        with st.chat_message(
            "user",
            avatar=str(Config.Path.IMAGES_DIR / "user-avatar.jfif"),
        ):
            st.markdown(prompt)
        
        # Lưu vào database và đồng bộ với chain history
        conversation_id = st.session_state.get("current_conversation_id", "default")
        add_message_to_history(conversation_id, "user", prompt)
        
        # Cập nhật title nếu đây là tin nhắn đầu tiên của user
        if len([msg for msg in st.session_state.messages if msg["role"] == "user"]) == 1:
            storage = get_chat_storage()
            title = prompt[:50] + "..." if len(prompt) > 50 else prompt
            storage.update_conversation_title(conversation_id, title)
        
        try:
            # Try using our improved async handler
            run_async_in_streamlit(ask_chain, prompt, chain)
        except RuntimeError as e:
            st.error(f"Runtime error (handled): {e}")
            # Fall back to a synchronous approach if needed
            full_response = "Xin lỗi, mình đang gặp vấn đề kỹ thuật. Bạn có thể thử lại không?"
            with st.chat_message(
                "assistant", avatar=str(Config.Path.IMAGES_DIR / "assistant-avatar.jfif")
            ):
                st.markdown(full_response)
            
            # Save the message to history
            current_time = datetime.datetime.now().strftime("%H:%M")
            st.session_state.messages.append({
                "role": "assistant", 
                "content": full_response,
                "timestamp": current_time
            })
            
            # Lưu vào database
            add_message_to_history(conversation_id, "assistant", full_response)

def load_conversation(conversation_id):
    """Tải một cuộc trò chuyện từ database"""
    storage = get_chat_storage()
    messages = storage.get_conversation_messages(conversation_id)
    
    if messages:
        st.session_state.messages = messages
        st.session_state.current_conversation_id = conversation_id
        
        # Load lịch sử vào chain history
        load_history_from_db(conversation_id)
        
        st.rerun()
    else:
        st.error("Không thể tải cuộc trò chuyện này")

def create_new_conversation():
    """Tạo cuộc trò chuyện mới"""
    storage = get_chat_storage()
    conversation_id = storage.create_conversation()
    
    current_time = datetime.datetime.now().strftime("%H:%M")
    initial_message = {
        "role": "assistant",
        "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
        "timestamp": current_time
    }
    
    st.session_state.messages = [initial_message]
    st.session_state.current_conversation_id = conversation_id
    
    # Lưu tin nhắn chào hỏi vào database
    storage.save_message(conversation_id, "assistant", initial_message["content"], current_time)
    
    st.rerun()

def delete_conversation(conversation_id):
    """Xóa một cuộc trò chuyện"""
    storage = get_chat_storage()
    storage.delete_conversation(conversation_id)
    
    if st.session_state.get("current_conversation_id") == conversation_id:
        create_new_conversation()
    else:
        st.rerun()


def get_base64_of_image(image_path):
    """Chuyển đổi hình ảnh thành chuỗi base64"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string

def create_sidebar():
    with st.sidebar:
        if st.button("+ Cuộc trò chuyện mới", use_container_width=True, key="new_chat_btn"):
            create_new_conversation()
        
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
        
        storage = get_chat_storage()
        all_conversations = storage.get_all_conversations()
        
        if all_conversations:
            for conv in all_conversations:
                with st.container():
                    col1, col2 = st.columns([3, 0.5])
                    with col1:
                        is_current = st.session_state.get("current_conversation_id") == conv.get("id")
                        button_label = f"🔹 {conv['title']}" if is_current else f"{conv['title']}"
                        if st.button(button_label, key=f"btn_{conv['id']}", use_container_width=True):
                            load_conversation(conv['id'])
                    with col2:
                        if st.button("🗑️", key=f"del_{conv['id']}", help="Xóa cuộc trò chuyện này"):
                            delete_conversation(conv['id'])
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
    
    div[data-testid="stMainBlockContainer"] {
        padding: 0 4rem !important;
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
    
   
    .st-emotion-cache-1lm6gnd {
        display: none !important;
    }
    .st-emotion-cache-hu32sh {
        background: unset !important;
    }
    
    button[data-testid="chatSubmitButton"] {
        border-radius: 50%;
    }
    
    .st-emotion-cache-1f3w014 {
        fill: #5BC099;
    }
    
    button[data-testid="stChatInputSubmitButton"]:hover {
        background: unset !important;
    }
    
    .stButton button:hover {
        background-color: #f0f7ff !important;
    }
    
    .stChatInput > div,
    .st-b1 {
        background: white !important;
        # padding: 2rem;
    }
    
    textarea {
        color: black !important;
        background: white !important;
        caret-color: black !important;
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
    # Kiểm tra xem có cuộc trò chuyện nào đang mở không
    if "current_conversation_id" not in st.session_state:
        # Tạo cuộc trò chuyện mới
        storage = get_chat_storage()
        conversation_id = storage.create_conversation()
        st.session_state.current_conversation_id = conversation_id
        
        current_time = datetime.datetime.now().strftime("%H:%M")
        initial_message = {
            "role": "assistant",
            "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
            "timestamp": current_time
        }
        
        st.session_state.messages = [initial_message]
        
        # Lưu tin nhắn chào hỏi vào database
        storage.save_message(conversation_id, "assistant", initial_message["content"], current_time)
    else:
        # Load cuộc trò chuyện hiện tại
        conversation_id = st.session_state.current_conversation_id
        storage = get_chat_storage()
        messages = storage.get_conversation_messages(conversation_id)
        if messages:
            st.session_state.messages = messages
        else:
            # Nếu không có tin nhắn, tạo tin nhắn chào hỏi
            current_time = datetime.datetime.now().strftime("%H:%M")
            initial_message = {
                "role": "assistant",
                "content": "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?",
                "timestamp": current_time
            }
            st.session_state.messages = [initial_message]
            storage.save_message(conversation_id, "assistant", initial_message["content"], current_time)
    
create_sidebar()

chat_container = st.container()

with chat_container:
    with st.spinner("Starting..."):
        chain = build_qa_chain()
    
    show_message_history()

show_chat_input(chain)
