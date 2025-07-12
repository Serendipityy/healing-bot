# Quick Start Guide for Healing Bot

## 🚀 Cách chạy nhanh nhất

### Bước 1: Chuẩn bị môi trường
```cmd
# Đảm bảo Qdrant đang chạy
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest

# Hoặc nếu đã có Qdrant chạy ở localhost:6333, bỏ qua bước này
```

### Bước 2: Cài đặt dependencies
```cmd
# Cài đặt tất cả dependencies
pip install -r requirements.txt
```

### Bước 3: Chạy Backend (Terminal 1)
```cmd
cd backend
python main.py
```

**⏳ Đợi thông báo: "🎉 Ready to process chat requests!"**

### Bước 4: Chạy Frontend (Terminal 2) 
```cmd
cd frontend
streamlit run app.py
```

### Truy cập:
- **Frontend (UI)**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## ✨ Cải tiến mới:

### 🔄 Preloading Models
- **Backend** sẽ load tất cả models khi khởi động
- **Frontend** sẽ hiển thị progress loading
- **Chat** sẽ response ngay lập tức sau khi models đã load

### � Health Checks
- `GET /health` - Tình trạng models
- `GET /ready` - Kiểm tra sẵn sàng
- Frontend tự động check và hiển thị trạng thái

## �🔧 Troubleshooting

### Lỗi import:
- Đảm bảo file `.env` tồn tại
- Đảm bảo thư mục `ragbase/` còn nguyên
- Chạy từ thư mục gốc `healing-bot/`

### Lỗi connection:
- Kiểm tra Qdrant: curl http://localhost:6333/health
- Kiểm tra Backend: curl http://localhost:8000/health
- Kiểm tra Ready: curl http://localhost:8000/ready

### Models loading lâu:
- Chờ thông báo "Ready to process chat requests!"
- Frontend sẽ hiển thị progress bar
- Lần đầu có thể mất 1-2 phút

## 📝 Các file cần thiết:
- `.env` (API keys)
- `chat_history.db` (database - sẽ tự tạo)
- `ragbase/` (thư mục gốc)
- `config/` (cấu hình)
- `images/` (hình ảnh UI)
