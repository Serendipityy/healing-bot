# Healing Bot - Refactored Architecture

## 🔄 Major Refactoring

Dự án đã được refactor hoàn toàn để giải quyết các vấn đề về async handling và tách biệt Backend/Frontend một cách rõ ràng.

## 🏗️ Kiến trúc mới

### Backend (FastAPI)
```
backend/
├── main.py              # FastAPI application
├── models/              # Pydantic models
│   └── chat_models.py
├── services/            # Business logic
│   ├── chat_service.py  # Chat management
│   └── rag_service.py   # RAG processing
└── config/              # Configuration
    └── settings.py
```

### Frontend (Streamlit)
```
frontend/
├── app.py              # Streamlit UI
├── api_client.py       # HTTP client for backend
└── ui_components.py    # UI components
```

## 🚀 Cách chạy

### 1. Cài đặt dependencies
```bash
pip install -r requirements_new.txt
```

### 2. Chạy ứng dụng
```bash
python run_servers.py
```

Lệnh này sẽ tự động khởi động:
- **Backend API**: http://localhost:8000
- **Frontend UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

### 3. Truy cập ứng dụng
Mở trình duyệt và vào: http://localhost:8501

## ✨ Lợi ích của kiến trúc mới

### 1. Loại bỏ async complications
- ❌ **Trước**: `nest_asyncio`, try-catch phức tạp, event loop conflicts
- ✅ **Sau**: FastAPI native async support, clean error handling

### 2. Tách biệt Frontend/Backend
- ❌ **Trước**: Tất cả logic trong 1 file app.py (566 dòng)
- ✅ **Sau**: Backend và Frontend riêng biệt, dễ maintain

### 3. Better Error Handling
- ❌ **Trước**: Try-catch khắp nơi, khó debug
- ✅ **Sau**: Centralized error handling, proper logging

### 4. Scalability
- ❌ **Trước**: Monolithic structure
- ✅ **Sau**: Microservice-ready, có thể scale riêng từng phần

## 🔧 Development

### Backend Development
```bash
# Chỉ chạy backend
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend Development  
```bash
# Chỉ chạy frontend (cần backend running)
streamlit run frontend/app.py --server.port 8501
```

## 📁 File Structure Comparison

### Trước (Old)
```
healing-bot/
└── app.py (566 lines - everything mixed together)
    ├── Streamlit UI
    ├── Async handling with nest_asyncio
    ├── RAG processing  
    ├── Chat storage
    ├── Event loop management
    └── UI styling
```

### Sau (New)
```
healing-bot/
├── backend/                 # 🔧 Pure Python async backend
│   ├── main.py             # FastAPI app
│   ├── services/           # Business logic
│   ├── models/             # Data models
│   └── config/             # Settings
├── frontend/               # 🎨 Clean Streamlit UI
│   ├── app.py              # UI only
│   ├── api_client.py       # HTTP client
│   └── ui_components.py    # UI components
└── run_servers.py          # 🚀 Server orchestration
```

## 🛠️ Technical Improvements

1. **Async Handling**: 
   - FastAPI handles async natively
   - No more `nest_asyncio` complications
   - Clean async/await patterns

2. **Error Management**:
   - Proper HTTP status codes
   - Centralized error handling
   - Better user feedback

3. **Code Organization**:
   - Single Responsibility Principle
   - Separated concerns
   - Easier testing and maintenance

4. **Performance**:
   - Streaming responses
   - Efficient resource management
   - Better memory usage

## 🔄 Migration from Old Version

Các file cũ vẫn được giữ lại để tham khảo:
- `app.py` (original) - File gốc
- `app_new.py` - File thông báo về kiến trúc mới

Để chuyển sang kiến trúc mới, simply run:
```bash
python run_servers.py
```

## 🐛 Troubleshooting

### Backend không start được
```bash
# Check port 8000
netstat -an | grep 8000

# Run backend directly
cd backend
python -m uvicorn main:app --reload
```

### Frontend không kết nối được Backend
```bash
# Check backend health
curl http://localhost:8000/health

# Check Qdrant connection
curl http://localhost:6333/health
```

### Lỗi dependencies
```bash
pip install -r requirements_new.txt --upgrade
```

## 📝 Notes

- Đảm bảo Qdrant server đang chạy trên localhost:6333
- Backend phải start trước Frontend
- Database sẽ được tự động khởi tạo khi backend start
