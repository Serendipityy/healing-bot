import sqlite3
import json
import datetime
import os
from pathlib import Path

class ChatStorage:
    def __init__(self, db_file="chat_history.db"):
        """
        Khởi tạo lưu trữ chat với database SQLite
        """
        self.db_file = db_file
        self._init_db()
        
    def _init_db(self):
        """
        Khởi tạo cấu trúc database nếu chưa tồn tại
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create the main table to store conversation information
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            preview TEXT,
            date TEXT,
            is_real_conversation INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create the table to store messages
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_chat(self, chat_data):
        """
        Lưu một cuộc trò chuyện vào database
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        chat_id = chat_data.get('id')
        preview = chat_data.get('preview', 'Cuộc hội thoại mới')
        date = chat_data.get('date', datetime.datetime.now().strftime("%d/%m/%Y"))
        is_real_conversation = 1 if chat_data.get('is_real_conversation', False) else 0
        
        # Check if the chat already exists to perform UPDATE or INSERT
        cursor.execute("SELECT id FROM chats WHERE id = ?", (chat_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing chat
            cursor.execute(
                "UPDATE chats SET preview = ?, date = ?, is_real_conversation = ? WHERE id = ?",
                (preview, date, is_real_conversation, chat_id)
            )
        else:
            # Add new chat
            cursor.execute(
                "INSERT INTO chats (id, preview, date, is_real_conversation) VALUES (?, ?, ?, ?)",
                (chat_id, preview, date, is_real_conversation)
            )
        
        # Delete old messages before adding new ones to avoid duplication
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        
        # Add the messages
        messages = chat_data.get('messages', [])
        for message in messages:
            cursor.execute(
                "INSERT INTO messages (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (
                    chat_id, 
                    message.get('role', ''), 
                    message.get('content', ''),
                    message.get('timestamp', datetime.datetime.now().strftime("%H:%M"))
                )
            )
        
        conn.commit()
        conn.close()
        return chat_data
    
    def get_all_chats(self):
        """
        Lấy tất cả lịch sử chat từ database
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, preview, date, is_real_conversation FROM chats ORDER BY created_at DESC"
        )
        
        chats = []
        for row in cursor.fetchall():
            chats.append({
                'id': row['id'],
                'preview': row['preview'],
                'date': row['date'],
                'is_real_conversation': bool(row['is_real_conversation'])
            })
        
        conn.close()
        return chats
    
    def get_chat_by_id(self, chat_id):
        """
        Lấy chi tiết một cuộc trò chuyện theo ID
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, preview, date, is_real_conversation FROM chats WHERE id = ?",
            (chat_id,)
        )
        
        chat_row = cursor.fetchone()
        if not chat_row:
            conn.close()
            return None
        
        cursor.execute(
            "SELECT role, content, timestamp FROM messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,)
        )
        
        messages = []
        for msg_row in cursor.fetchall():
            messages.append({
                'role': msg_row['role'],
                'content': msg_row['content'],
                'timestamp': msg_row['timestamp']
            })
        
        chat_data = {
            'id': chat_row['id'],
            'preview': chat_row['preview'],
            'date': chat_row['date'],
            'is_real_conversation': bool(chat_row['is_real_conversation']),
            'messages': messages
        }
        
        conn.close()
        return chat_data
    
    def delete_chat(self, chat_id):
        """
        Xóa một cuộc trò chuyện
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def generate_chat_id(self):
        """
        Tạo ID duy nhất cho cuộc trò chuyện mới
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return f"chat_{timestamp}"