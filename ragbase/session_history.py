from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
import os
import sys

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.chat_storage import ChatStorage

# Global storage cho chain history
chain_histories = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    """
    Lấy lịch sử chat cho chain, đồng bộ với database
    """
    if session_id not in chain_histories:
        chain_histories[session_id] = ChatMessageHistory()
        
        # Load lịch sử từ database nếu có
        if session_id and session_id != "session-id-42":
            load_history_from_db(session_id)
    
    return chain_histories[session_id]

def load_history_from_db(conversation_id: str):
    """
    Load lịch sử từ database vào chain history
    """
    try:
        # Get project root path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, "chat_history.db")
        
        if os.path.exists(db_path):
            storage = ChatStorage(db_path)
            messages = storage.get_conversation_messages(conversation_id)
            
            if conversation_id not in chain_histories:
                chain_histories[conversation_id] = ChatMessageHistory()
            
            # Clear existing messages
            chain_histories[conversation_id].clear()
            
            # Add messages from database
            for msg in messages:
                if msg['role'] == 'user':
                    chain_histories[conversation_id].add_message(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    chain_histories[conversation_id].add_message(AIMessage(content=msg['content']))
    except Exception as e:
        print(f"Error loading history from DB: {e}")

def save_message_to_db(conversation_id: str, role: str, content: str):
    """
    Lưu tin nhắn vào database
    """
    try:
        # Get project root path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, "chat_history.db")
        storage = ChatStorage(db_path)
        storage.save_message(conversation_id, role, content)
    except Exception as e:
        print(f"Error saving message to DB: {e}")

def add_message_to_history(conversation_id: str, role: str, content: str):
    """
    Thêm tin nhắn vào cả chain history và database
    """
    # Thêm vào chain history
    if conversation_id not in chain_histories:
        chain_histories[conversation_id] = ChatMessageHistory()
    
    if role == 'user':
        chain_histories[conversation_id].add_message(HumanMessage(content=content))
    elif role == 'assistant':
        chain_histories[conversation_id].add_message(AIMessage(content=content))
    
    # Lưu vào database
    save_message_to_db(conversation_id, role, content)

def clear_session_history(session_id: str):
    """
    Xóa lịch sử của một session
    """
    if session_id in chain_histories:
        chain_histories[session_id].clear()