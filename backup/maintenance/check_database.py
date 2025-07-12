#!/usr/bin/env python3
"""
Script để kiểm tra database sau khi test UI
"""
import sqlite3
import os

def check_database():
    db_path = "chat_history.db"
    
    if os.path.exists(db_path):
        print(f"✅ Database found: {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Kiểm tra tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 Tables found: {[table[0] for table in tables]}")
        
        # Kiểm tra conversations
        cursor.execute('SELECT COUNT(*) as count FROM conversations')
        conv_count = cursor.fetchone()[0]
        print(f"💬 Number of conversations: {conv_count}")
        
        if conv_count > 0:
            cursor.execute('SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT 5')
            conversations = cursor.fetchall()
            print('\n📝 Recent conversations:')
            for conv in conversations:
                print(f"  ID: {conv['id'][:8]}... | Title: {conv['title']} | Updated: {conv['updated_at']}")
        
        # Kiểm tra messages
        cursor.execute('SELECT COUNT(*) as count FROM messages')
        msg_count = cursor.fetchone()[0]
        print(f"\n💌 Total messages: {msg_count}")
        
        if msg_count > 0:
            cursor.execute('''
                SELECT conversation_id, role, content, timestamp, message_order 
                FROM messages 
                ORDER BY id DESC LIMIT 10
            ''')
            messages = cursor.fetchall()
            print('\n📨 Recent messages:')
            for msg in messages:
                content_preview = msg['content'][:50] + '...' if len(msg['content']) > 50 else msg['content']
                print(f"  [{msg['message_order']}] {msg['role']}: {content_preview} ({msg['timestamp']})")
                
        # Kiểm tra chi tiết cuộc trò chuyện gần nhất
        if conv_count > 0:
            cursor.execute('SELECT id FROM conversations ORDER BY updated_at DESC LIMIT 1')
            latest_conv_id = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT role, content, timestamp, message_order 
                FROM messages 
                WHERE conversation_id = ? 
                ORDER BY message_order ASC
            ''', (latest_conv_id,))
            
            conv_messages = cursor.fetchall()
            print(f"\n🔍 Latest conversation details ({latest_conv_id[:8]}...):")
            for msg in conv_messages:
                content_preview = msg['content'][:80] + '...' if len(msg['content']) > 80 else msg['content']
                print(f"  {msg['role']}: {content_preview}")
        
        conn.close()
    else:
        print("❌ Database file not found!")

if __name__ == "__main__":
    check_database()
