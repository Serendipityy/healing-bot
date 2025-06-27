"""
Chat service for managing chat sessions and messages
"""
import uuid
import datetime
from typing import List, Optional, Dict, Any
import aiosqlite
import json
from pathlib import Path

from backend.models.chat_models import ChatHistory, ChatMessage

class ChatService:
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._init_db_sync()
    
    def _init_db_sync(self):
        """Initialize database synchronously - compatible with existing schema"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if not cursor.fetchone():
            # Create chats table
            cursor.execute("""
                CREATE TABLE chats (
                    id TEXT PRIMARY KEY,
                    preview TEXT,
                    date TEXT,
                    is_real_conversation INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            # Create messages table
            cursor.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
                )
            """)
        
        conn.commit()
        conn.close()
    
    async def create_chat(self, initial_message: Optional[str] = None) -> str:
        """Create a new chat session"""
        chat_id = str(uuid.uuid4())
        current_time = datetime.datetime.now().strftime("%H:%M")
        current_date = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Create initial assistant message
        assistant_message = "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?"
        
        preview = initial_message[:30] + "..." if initial_message and len(initial_message) > 30 else "Cuộc hội thoại mới"
        
        async with aiosqlite.connect(self.db_path) as db:
            # Create chat record
            await db.execute("""
                INSERT INTO chats (id, preview, date, is_real_conversation)
                VALUES (?, ?, ?, ?)
            """, (chat_id, preview, current_date, False))
            
            # Add initial assistant message
            await db.execute("""
                INSERT INTO messages (chat_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (chat_id, "assistant", assistant_message, current_time))
            
            # Add initial user message if provided
            if initial_message:
                await db.execute("""
                    INSERT INTO messages (chat_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (chat_id, "user", initial_message, current_time))
            
            await db.commit()
        
        return chat_id
    
    async def save_message(self, chat_id: str, role: str, content: str) -> bool:
        """Save a message to a chat session"""
        current_time = datetime.datetime.now().strftime("%H:%M")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Add message to messages table
            await db.execute("""
                INSERT INTO messages (chat_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (chat_id, role, content, current_time))
            
            # Update chat preview if it's a user message
            if role == "user" and content:
                preview = content[:30] + "..." if len(content) > 30 else content
                await db.execute("""
                    UPDATE chats 
                    SET preview = ?, is_real_conversation = 1
                    WHERE id = ?
                """, (preview, chat_id))
            else:
                # Mark as real conversation
                await db.execute("""
                    UPDATE chats 
                    SET is_real_conversation = 1
                    WHERE id = ?
                """, (chat_id,))
            
            await db.commit()
            return True
    
    async def get_chat_history(self, chat_id: str) -> Optional[ChatHistory]:
        """Get chat history for a specific chat"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get chat info
            cursor = await db.execute("""
                SELECT id, preview, date, is_real_conversation 
                FROM chats WHERE id = ?
            """, (chat_id,))
            chat_row = await cursor.fetchone()
            
            if not chat_row:
                return None
            
            # Get messages
            cursor = await db.execute("""
                SELECT role, content, timestamp 
                FROM messages 
                WHERE chat_id = ? 
                ORDER BY id ASC
            """, (chat_id,))
            message_rows = await cursor.fetchall()
            
            messages = [
                ChatMessage(role=row[0], content=row[1], timestamp=row[2])
                for row in message_rows
            ]
            
            return ChatHistory(
                id=chat_row[0],
                preview=chat_row[1],
                date=chat_row[2],
                messages=messages,
                is_real_conversation=bool(chat_row[3])
            )
    
    async def get_all_chats(self) -> List[ChatHistory]:
        """Get all chat sessions"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, preview, date, is_real_conversation
                FROM chats 
                WHERE is_real_conversation = 1
                ORDER BY created_at DESC
            """)
            chat_rows = await cursor.fetchall()
            
            chats = []
            for chat_row in chat_rows:
                # Get messages for this chat
                msg_cursor = await db.execute("""
                    SELECT role, content, timestamp 
                    FROM messages 
                    WHERE chat_id = ? 
                    ORDER BY id ASC
                """, (chat_row[0],))
                message_rows = await msg_cursor.fetchall()
                
                messages = [
                    ChatMessage(role=row[0], content=row[1], timestamp=row[2])
                    for row in message_rows
                ]
                
                chats.append(ChatHistory(
                    id=chat_row[0],
                    preview=chat_row[1],
                    date=chat_row[2],
                    messages=messages,
                    is_real_conversation=bool(chat_row[3])
                ))
            
            return chats
    
    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat session"""
        async with aiosqlite.connect(self.db_path) as db:
            # Delete messages first (due to foreign key constraint)
            await db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            # Delete chat
            cursor = await db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    async def close(self):
        """Close any open connections"""
        # aiosqlite handles connections per operation, so no cleanup needed
        pass
