# 🔄 REFACTOR: Hệ thống lịch sử trò chuyện mới

## ⚠️ Thay đổi quan trọng

Đã **hoàn toàn refactor** hệ thống lưu trữ và quản lý lịch sử trò chuyện để giải quyết vấn đề chatbot không nhớ được context giữa các tin nhắn.

## 🗂️ Cấu trúc database mới

### Bảng `conversations`
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,                    -- UUID unique cho mỗi cuộc trò chuyện
    title TEXT NOT NULL,                    -- Tiêu đề cuộc trò chuyện
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng `messages`
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,          -- Liên kết với conversations
    role TEXT NOT NULL,                     -- 'user' hoặc 'assistant'
    content TEXT NOT NULL,                  -- Nội dung tin nhắn
    timestamp TEXT,                         -- Thời gian hiển thị (HH:MM)
    message_order INTEGER,                  -- Thứ tự tin nhắn trong cuộc trò chuyện
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

## 🔧 Các thay đổi chính

### 1. **Thống nhất hệ thống lưu trữ**
- ❌ **Trước:** 2 hệ thống riêng biệt và không đồng bộ
  - `st.session_state.messages` (UI)
  - `ragbase.session_history` (Chain)
- ✅ **Sau:** 1 hệ thống duy nhất, đồng bộ giữa UI và Chain

### 2. **Loại bỏ các field không cần thiết**
- ❌ Xóa `is_real_conversation` - tất cả cuộc trò chuyện đều quan trọng
- ❌ Xóa `preview` - sử dụng `title` thay thế
- ❌ Xóa `date` - sử dụng `created_at` và `updated_at`

### 3. **API mới đơn giản hơn**

#### ChatStorage
```python
# Tạo cuộc trò chuyện mới
conversation_id = storage.create_conversation(title="Tiêu đề")

# Lưu tin nhắn
storage.save_message(conversation_id, "user", "Nội dung", "14:30")

# Lấy tin nhắn
messages = storage.get_conversation_messages(conversation_id)

# Lấy danh sách cuộc trò chuyện
conversations = storage.get_all_conversations()
```

#### Session History (đồng bộ với database)
```python
# Thêm tin nhắn vào cả chain history và database
add_message_to_history(conversation_id, "user", "Nội dung")

# Load lịch sử từ database vào chain
load_history_from_db(conversation_id)

# Lấy session history cho chain
history = get_session_history(conversation_id)
```

## 🚀 Cải thiện

### ✅ **Đã sửa các vấn đề:**
1. **Chatbot nhớ được context** - Chain history được đồng bộ với database
2. **Lịch sử đồng nhất** - UI và Chain sử dụng cùng nguồn dữ liệu
3. **Code gọn gàng** - Loại bỏ duplicate logic
4. **Database tối ưu** - Cấu trúc đơn giản, có index
5. **Dễ quản lý** - API rõ ràng, test coverage

### 🔄 **Luồng hoạt động mới:**
1. User gửi tin nhắn → Lưu vào database + thêm vào chain history
2. Assistant trả lời → Lưu vào database + thêm vào chain history  
3. Load cuộc trò chuyện → Đồng bộ từ database vào UI và chain history
4. Chain sử dụng full history → Context được bảo toàn

## 📁 Files đã thay đổi

- `chat_storage.py` - **Hoàn toàn viết lại**
- `ragbase/session_history.py` - **Hoàn toàn viết lại** 
- `app.py` - **Refactor major** các function liên quan đến history
- `test_database.py` - **Mới** - test coverage cho hệ thống

## 🏃‍♂️ Để chạy

```bash
cd healing-bot
streamlit run app.py
```

Database sẽ được tạo tự động với cấu trúc mới. Lịch sử cũ sẽ bị xóa (cần thiết để đảm bảo tính nhất quán).

## 🧪 Test

```bash
python test_database.py
```

Tất cả tests đều pass ✅
