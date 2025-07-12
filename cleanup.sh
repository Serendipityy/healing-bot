#!/bin/bash

echo "🧹 Cleaning up old files after refactoring..."

# Create backup directory if not exists
mkdir -p backup

echo "📦 Moving old files to backup..."

# Move the original monolithic app.py
if [ -f "app.py" ]; then
    echo "Moving app.py to backup..."
    mv app.py backup/app_original.py
fi

# Move __pycache__ directories
if [ -d "__pycache__" ]; then
    echo "Moving __pycache__ to backup..."
    mv __pycache__ backup/__pycache___root
fi

if [ -d "frontend/__pycache__" ]; then
    echo "Moving frontend __pycache__..."
    mv frontend/__pycache__ backup/__pycache___frontend
fi

if [ -d "backend/__pycache__" ]; then
    echo "Moving backend __pycache__..."
    mv backend/__pycache__ backup/__pycache___backend
fi

# Clean up any .pyc files
echo "🗑️ Removing .pyc files..."
find . -name "*.pyc" -delete 2>/dev/null

echo "✅ Cleanup completed!"
echo "📁 Backed up files are in the 'backup' folder"
echo "🚀 Your refactored project is now clean and ready to use"
