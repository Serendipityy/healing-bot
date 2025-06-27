@echo off
echo 🤗 Healing Bot - Starting servers...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv\" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

echo 📥 Installing/updating dependencies...
pip install -r requirements_new.txt

echo 🚀 Starting Healing Bot servers...
python run_servers.py

pause
