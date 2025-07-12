#!/bin/bash

# Development startup script

echo "🚀 Starting Healing Bot Development Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one with your API keys."
    exit 1
fi

# Start Qdrant if not running
echo "🔍 Checking Qdrant..."
if ! curl -s http://localhost:6333/health > /dev/null; then
    echo "🐳 Starting Qdrant..."
    docker run -d --name qdrant -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant:latest
    sleep 5
else
    echo "✅ Qdrant is already running"
fi

# Function to run backend
run_backend() {
    echo "🔧 Starting Backend..."
    cd backend
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Function to run frontend
run_frontend() {
    echo "🎨 Starting Frontend..."
    cd frontend
    streamlit run app.py --server.port=8501 --server.address=0.0.0.0
}

# Check command line argument
case "$1" in
    "backend")
        run_backend
        ;;
    "frontend")
        run_frontend
        ;;
    "both")
        echo "🔄 Starting both backend and frontend..."
        run_backend &
        sleep 3
        run_frontend &
        wait
        ;;
    *)
        echo "Usage: $0 {backend|frontend|both}"
        echo "  backend  - Start only the FastAPI backend"
        echo "  frontend - Start only the Streamlit frontend"
        echo "  both     - Start both services"
        exit 1
        ;;
esac
