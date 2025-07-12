@echo off
echo 🧹 Cleaning up old files after refactoring...

REM Create backup directory if not exists
if not exist backup mkdir backup

echo 📦 Moving old files to backup...

REM Move the original monolithic app.py
if exist app.py (
    echo Moving app.py to backup...
    move app.py backup\app_original.py
)

REM Move __pycache__ directories
if exist __pycache__ (
    echo Moving __pycache__ to backup...
    move __pycache__ backup\__pycache___root
)

if exist frontend\__pycache__ (
    echo Moving frontend __pycache__...
    move frontend\__pycache__ backup\__pycache___frontend
)

if exist backend\__pycache__ (
    echo Moving backend __pycache__...
    move backend\__pycache__ backup\__pycache___backend
)

REM Clean up any .pyc files
echo 🗑️ Removing .pyc files...
for /r %%i in (*.pyc) do del "%%i" 2>nul

echo ✅ Cleanup completed!
echo 📁 Backed up files are in the 'backup' folder
echo 🚀 Your refactored project is now clean and ready to use

pause
