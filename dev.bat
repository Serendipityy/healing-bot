@echo off
echo 🚀 Starting Healing Bot Development Environment

REM Check if .env file exists
if not exist .env (
    echo ❌ .env file not found. Please create one with your API keys.
    exit /b 1
)

REM Check if Qdrant is running
echo 🔍 Checking Qdrant...
curl -s http://localhost:6333/health >nul 2>&1
if errorlevel 1 (
    echo 🐳 Starting Qdrant...
    docker run -d --name qdrant -p 6333:6333 -v "%cd%\qdrant_data:/qdrant/storage" qdrant/qdrant:latest
    timeout /t 5 /nobreak >nul
) else (
    echo ✅ Qdrant is already running
)

REM Check command line argument
if "%1"=="backend" (
    echo 🔧 Starting Backend...
    cd backend
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
) else if "%1"=="frontend" (
    echo 🎨 Starting Frontend...
    cd frontend
    streamlit run app.py --server.port=8501 --server.address=0.0.0.0
) else if "%1"=="both" (
    echo 🔄 Starting both backend and frontend...
    start "Backend" cmd /c "cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    timeout /t 3 /nobreak >nul
    start "Frontend" cmd /c "cd frontend && streamlit run app.py --server.port=8501 --server.address=0.0.0.0"
) else (
    echo Usage: %0 {backend^|frontend^|both}
    echo   backend  - Start only the FastAPI backend
    echo   frontend - Start only the Streamlit frontend
    echo   both     - Start both services
    exit /b 1
)
