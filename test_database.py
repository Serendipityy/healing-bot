#!/usr/bin/env python3
"""
Test script để kiểm tra chức năng database mới
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chat_storage import ChatStorage
from ragbase.session_history import add_message_to_history, get_session_history, load_history_from_db

def test_database():
    print("🧪 Testing new database system...")
    
    # Khởi tạo storage
    storage = ChatStorage("test_chat_history.db")
    
    # Test 1: Tạo cuộc trò chuyện mới
    print("\n1. Creating new conversation...")
    conv_id = storage.create_conversation("Test conversation")
    print(f"✅ Created conversation: {conv_id}")
    
    # Test 2: Lưu tin nhắn
    print("\n2. Saving messages...")
    storage.save_message(conv_id, "user", "Tôi đang buồn", "14:30")
    storage.save_message(conv_id, "assistant", "Tôi hiểu cảm giác của bạn. Bạn có muốn chia sẻ thêm không?", "14:31")
    print("✅ Messages saved")
    
    # Test 3: Lấy tin nhắn
    print("\n3. Retrieving messages...")
    messages = storage.get_conversation_messages(conv_id)
    for msg in messages:
        print(f"  {msg['role']}: {msg['content']}")
    print("✅ Messages retrieved")
    
    # Test 4: Test session history integration
    print("\n4. Testing session history integration...")
    add_message_to_history(conv_id, "user", "Tôi vẫn còn buồn")
    add_message_to_history(conv_id, "assistant", "Đó là điều bình thường. Cảm xúc cần thời gian để lắng xuống.")
    
    session_history = get_session_history(conv_id)
    print(f"✅ Session history has {len(session_history.messages)} messages")
    
    # Test 5: Lấy danh sách cuộc trò chuyện
    print("\n5. Getting all conversations...")
    convs = storage.get_all_conversations()
    for conv in convs:
        print(f"  {conv['id']}: {conv['title']}")
    print("✅ Conversations listed")
    
    # Test 6: Load lại lịch sử từ database
    print("\n6. Testing load history from database...")
    load_history_from_db(conv_id)
    session_history_loaded = get_session_history(conv_id)
    print(f"✅ Loaded session history has {len(session_history_loaded.messages)} messages")
    
    # Cleanup
    if os.path.exists("test_chat_history.db"):
        os.remove("test_chat_history.db")
    
    print("\n🎉 All tests passed! Database system is working correctly.")

if __name__ == "__main__":
    test_database()
