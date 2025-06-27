# 🚀 Healing Bot - Performance Optimization Guide

## ⚡ Giải quyết vấn đề loading lâu

### 🔍 Nguyên nhân chính làm loading lâu:

1. **Embedding Models** (5-8 giây) - Load HuggingFace models
2. **Document Loading** (2-3 giây) - Đọc và xử lý Excel files 
3. **Vector Store Setup** (1-2 giây) - Kết nối Qdrant
4. **Retrievers & Rerankers** (2-4 giây) - Tạo các component phức tạp
5. **Chain Building** (1 giây) - Ghép nối các thành phần

**Tổng cộng: 15-20 giây** cho full initialization

### 🛠️ Các tối ưu đã implement:

## 1. **Detailed Progress Indicators**
```
🔧 Initializing RAG service...
  📡 Connecting to Qdrant...
  🤖 Loading language model...
  📊 Loading embedding model (this takes the longest)...
    ✅ Embedding model loaded in 7.23s
  📚 Loading documents...
    ✅ Documents loaded in 2.45s
  🗄️ Setting up vector stores...
    ✅ Vector stores ready in 1.12s
```

## 2. **Fast Mode (Development)**
Chạy với: `python run_optimized.py --fast`

**Khởi động**: 5-15 giây thay vì 15-30 giây

**Cách hoạt động**:
- ✅ Load minimal components trước
- ✅ Lazy loading - chỉ load khi cần
- ✅ Chỉ dùng summary retriever (nhanh hơn)
- ✅ Skip rerankers/filters cho đến khi cần
- ✅ Full components load khi có tin nhắn đầu tiên

## 3. **Full Mode (Production)**  
Chạy với: `python run_optimized.py` (default)

**Khởi động**: 15-30 giây (đầy đủ tính năng)

**Tính năng**:
- ✅ Load tất cả components
- ✅ Both full & summary retrievers
- ✅ All rerankers và filters
- ✅ Best response quality

## 🚀 Cách sử dụng:

### Option 1: Interactive Launcher
```bash
start_optimized.bat
```
Sẽ hiển thị menu cho phép chọn mode

### Option 2: Direct Commands  
```bash
# Fast mode (development)
python run_optimized.py --fast

# Full mode (production)  
python run_optimized.py

# Help
python run_optimized.py --help
```

### Option 3: Batch Files
```bash
# Fast mode
start_optimized.bat fast

# Full mode
start_optimized.bat full
```

## 📊 Performance Comparison

| Aspect | Fast Mode | Full Mode |
|--------|-----------|-----------|
| **Startup Time** | 5-15s | 15-30s |
| **Memory Usage** | Lower | Higher |
| **Response Quality** | Good | Excellent |
| **Use Case** | Development | Production |
| **First Message** | +5s (lazy load) | Normal |
| **Subsequent Messages** | Normal | Normal |

## 🔧 Technical Details

### Fast Mode Implementation:
```python
# Quick init - only essentials
await service._quick_init()  # ~3-5 seconds

# Lazy load on first use
await service._ensure_full_init()  # ~8-12 seconds
```

### Progressive Loading:
```python
# Step-by-step with timing
print("📊 Loading embedding model...")
step_start = time.time()
self.embedding_model = create_embeddings()
step_time = time.time() - step_start
print(f"✅ Embedding model loaded in {step_time:.2f}s")
```

### Async Document Loading:
```python
# Load documents concurrently
async def load_docs():
    docs_task = loop.run_in_executor(None, load_documents_from_excel, path1)
    summary_task = loop.run_in_executor(None, load_summary_documents_from_excel, path2)
    return await asyncio.gather(docs_task, summary_task)
```

## 💡 Recommendations:

### For Development:
- ✅ Use **Fast Mode**: `python run_optimized.py --fast`
- ✅ Quick iterations and testing
- ✅ First message takes extra time (one-time lazy load)

### For Production:
- ✅ Use **Full Mode**: `python run_optimized.py`
- ✅ Complete initialization upfront
- ✅ Consistent response times

### For Demo:
- ✅ Use **Fast Mode** nếu cần demo nhanh
- ✅ Use **Full Mode** nếu cần chất lượng tốt nhất

## 🎯 Future Optimizations:

1. **Model Caching** - Cache embedding models locally
2. **Precomputed Embeddings** - Store embeddings in database
3. **Streaming Initialization** - Load components trong background
4. **Model Quantization** - Smaller, faster models
5. **CDN for Models** - Download from faster sources

## 🚨 Troubleshooting:

### Nếu Fast Mode vẫn lâu:
```bash
# Check Qdrant connection
curl http://localhost:6333/health

# Check disk space (for model downloads)
# Check network speed (for model downloads)
```

### Nếu Full Mode quá lâu:
```bash
# Disable rerankers temporarily
# Check system resources
# Consider using SSD instead of HDD
```

## 📈 Monitoring Performance:

Script sẽ hiển thị timing chi tiết:
```
✅ Embedding model loaded in 7.23s
✅ Documents loaded in 2.45s  
✅ Vector stores ready in 1.12s
✅ Retrievers created in 3.67s
✅ RAG service initialized in 14.47 seconds
```

Theo dõi các con số này để identify bottlenecks.

---

💡 **Tip**: Dùng Fast Mode cho development hàng ngày, Full Mode cho testing cuối cùng và production!
