# Healing Bot - Refactored Architecture

## 🏗️ Architecture Overview

This project has been refactored into a clean, modern architecture with separated concerns:

### Backend (FastAPI)
- **Location**: `backend/`
- **Port**: 8000
- **Purpose**: Handles all AI processing, database operations, and API endpoints

### Frontend (Streamlit)
- **Location**: `frontend/`
- **Port**: 8501
- **Purpose**: Provides the user interface and communicates with backend via API

## 📁 Project Structure

```
healing-bot/
├── backend/                    # FastAPI Backend
│   ├── api/                   # API endpoints
│   │   ├── chat.py           # Chat endpoints
│   │   └── conversations.py  # Conversation management
│   ├── models/               # Pydantic models
│   │   └── chat.py          # Chat-related models
│   ├── services/            # Business logic
│   │   ├── chat_service.py  # Chat processing service
│   │   └── conversation_service.py # Conversation management
│   ├── main.py             # FastAPI app entry point
│   ├── requirements.txt    # Backend dependencies
│   └── Dockerfile         # Backend container config
├── frontend/               # Streamlit Frontend
│   ├── components/        # UI components
│   │   ├── chat.py       # Chat interface
│   │   └── sidebar.py    # Sidebar with conversation history
│   ├── styles/           # CSS styles
│   │   └── main.py      # All CSS styles
│   ├── utils/           # Frontend utilities
│   │   └── api_client.py # API communication
│   ├── app.py          # Streamlit app entry point
│   ├── requirements.txt # Frontend dependencies
│   └── Dockerfile      # Frontend container config
├── shared/             # Shared types and utilities
│   └── types.py       # Common data types
├── ragbase/           # Original RAG components (unchanged)
├── docker-compose.yml # Docker orchestration
├── dev.bat           # Windows development script
└── dev.sh            # Linux/Mac development script
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)
- Qdrant vector database

### Method 1: Development Mode

#### Windows
```cmd
# Start both services
dev.bat both

# Or start individually
dev.bat backend
dev.bat frontend
```

#### Linux/Mac
```bash
# Make script executable
chmod +x dev.sh

# Start both services
./dev.sh both

# Or start individually
./dev.sh backend
./dev.sh frontend
```

### Method 2: Docker

```bash
# Build and start all services
docker-compose up --build

# Start in background
docker-compose up -d --build
```

### Method 3: Manual Setup

#### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

## 🔗 API Endpoints

### Chat Endpoints
- `POST /api/chat/stream` - Stream chat responses
- `POST /api/chat/message` - Send chat message (non-streaming)

### Conversation Endpoints
- `GET /api/conversations/` - Get all conversations
- `POST /api/conversations/` - Create new conversation
- `GET /api/conversations/{id}` - Get specific conversation
- `PUT /api/conversations/{id}/title` - Update conversation title
- `DELETE /api/conversations/{id}` - Delete conversation
- `GET /api/conversations/{id}/messages` - Get conversation messages

### Health Check
- `GET /health` - API health status

## 🎨 Frontend Features

### Clean Architecture
- **Components**: Modular UI components
- **Styles**: Centralized CSS management
- **Utils**: API client and helper functions

### Key Components
- **Chat Interface**: Real-time streaming chat
- **Sidebar**: Conversation history management
- **Responsive Design**: Modern, mobile-friendly UI

## 🔧 Backend Features

### Services
- **ChatService**: Handles AI processing and streaming
- **ConversationService**: Manages conversation persistence

### API Design
- **RESTful**: Clean REST API design
- **Streaming**: Real-time response streaming
- **Error Handling**: Comprehensive error management

## 🐳 Docker Deployment

The application includes full Docker support:

```yaml
# docker-compose.yml includes:
- Qdrant vector database
- FastAPI backend
- Streamlit frontend
```

## 🔒 Environment Configuration

Create a `.env` file with your configuration:

```env
# Add your API keys and configuration
OPENAI_API_KEY=your_key_here
# ... other environment variables
```

## 🔄 Migration from Original

The refactor maintains compatibility with the original codebase:

1. **ragbase/** directory remains unchanged
2. **Database** (chat_history.db) continues to work
3. **Configuration** files remain compatible
4. **Images** and assets are preserved

## 🧪 Development

### Backend Development
- FastAPI provides automatic API documentation at `http://localhost:8000/docs`
- Hot reload enabled for development
- Comprehensive logging and error handling

### Frontend Development
- Streamlit hot reload for UI changes
- Modular component architecture
- Separated CSS for easy styling

## 📝 Benefits of This Architecture

1. **Separation of Concerns**: Clear division between UI and business logic
2. **Scalability**: Backend can handle multiple frontend clients
3. **Maintainability**: Modular, clean code structure
4. **API-First**: Backend can be used by other applications
5. **Docker Ready**: Easy deployment and scaling
6. **Development Friendly**: Hot reload, clear error handling

## 🎯 Next Steps

1. Add authentication/authorization
2. Implement caching layers
3. Add comprehensive testing
4. Performance monitoring
5. Production deployment configuration
