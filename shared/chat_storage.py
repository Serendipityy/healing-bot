import sqlite3
import json
import datetime
import os
import uuid
from pathlib import Path

class ChatStorage:
    def __init__(self, db_file="chat_history.db"):
        """
        Khởi tạo lưu trữ chat với database SQLite - cấu trúc mới đơn giản
        """
        self.db_file = db_file
        self._init_db()
        
    def _init_db(self):
        """
        Khởi tạo cấu trúc database đơn giản hơn
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Bảng chính lưu trữ cuộc trò chuyện
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Bảng lưu trữ tin nhắn (bao gồm cả UI và chain history)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT,
            message_order INTEGER,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        ''')
        
        # Index để tăng tốc truy vấn
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_conversation 
        ON messages(conversation_id, message_order)
        ''')
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, title=None):
        """
        Tạo cuộc trò chuyện mới
        """
        conv_id = str(uuid.uuid4())
        if not title:
            title = f"Cuộc trò chuyện {datetime.datetime.now().strftime('%d/%m %H:%M')}"
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, title)
        )
        
        conn.commit()
        conn.close()
        return conv_id
    
    def save_message(self, conversation_id, role, content, timestamp=None):
        """
        Lưu một tin nhắn vào cuộc trò chuyện
        """
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%H:%M")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Lấy thứ tự tin nhắn tiếp theo
        cursor.execute(
            "SELECT COALESCE(MAX(message_order), 0) + 1 FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        message_order = cursor.fetchone()[0]
        
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp, message_order) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, timestamp, message_order)
        )
        
        # Cập nhật thời gian updated_at cho cuộc trò chuyện
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        
        conn.commit()
        conn.close()
    
    def get_conversation_messages(self, conversation_id):
        """
        Lấy tất cả tin nhắn của một cuộc trò chuyện theo thứ tự
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY message_order ASC",
            (conversation_id,)
        )
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'role': row['role'],
                'content': row['content'],
                'timestamp': row['timestamp']
            })
        
        conn.close()
        return messages
    
    def get_all_conversations(self):
        """
        Lấy danh sách tất cả cuộc trò chuyện
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        )
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'id': row['id'],
                'title': row['title'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        conn.close()
        return conversations
    
    def update_conversation_title(self, conversation_id, title):
        """
        Cập nhật tiêu đề cuộc trò chuyện
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, conversation_id)
        )
        
        conn.commit()
        conn.close()
    
    def delete_conversation(self, conversation_id):
        """
        Xóa một cuộc trò chuyện và tất cả tin nhắn
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def clear_conversation_messages(self, conversation_id):
        """
        Xóa tất cả tin nhắn trong cuộc trò chuyện nhưng giữ lại cuộc trò chuyện
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        
        conn.commit()
        conn.close()
        return True