@echo off
echo 🚀 Healing Bot - Quick Start

echo 📋 Checking prerequisites...

REM Check if Qdrant is running
curl -s http://localhost:6333/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Qdrant not running. Starting Qdrant...
    echo 🐳 Please run: docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
    pause
    exit /b 1
) else (
    echo ✅ Qdrant is running
)

REM Check .env file
if not exist .env (
    echo ❌ .env file not found. Please create it with your API keys.
    pause
    exit /b 1
) else (
    echo ✅ .env file found
)

echo.
echo 🎯 Choose what to start:
echo 1. Backend only (API)
echo 2. Frontend only (UI) 
echo 3. Both (Recommended)
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo 🔧 Starting Backend...
    cd backend
    python main.py
) else if "%choice%"=="2" (
    echo 🎨 Starting Frontend...
    cd frontend
    streamlit run app.py
) else if "%choice%"=="3" (
    echo 🔄 Starting both services...
    echo.
    echo 📝 Instructions:
    echo 1. Backend is starting and loading models...
    echo 2. Wait for "Ready to process chat requests!" message
    echo 3. Then open new terminal and run: cd frontend ^&^& streamlit run app.py
    echo 4. Access UI at: http://localhost:8501
    echo.
    echo 💡 Tip: Frontend will show loading progress while models load
    echo.
    cd backend
    python main.py
) else (
    echo ❌ Invalid choice
    pause
    exit /b 1
)
