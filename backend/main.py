"""
Healing Bot Backend - FastAPI Application

Main entry point for the Healing Bot backend API server.
Provides RESTful endpoints for chat functionality and conversation management.
"""

import sys
import os

# Add the parent directory to sys.path to import from ragbase
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import chat_router, conversations_router
from backend.services import get_chat_service

# Create FastAPI app
app = FastAPI(
    title="Healing Bot API",
    description="Backend API for Healing Bot chatbot",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Initializing Healing Bot services...")
    # This will trigger the initialization of chat service and all models
    chat_service = get_chat_service()
    print("✅ All services initialized successfully!")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(conversations_router)


@app.get("/")
async def root():
    return {"message": "Healing Bot API is running"}


@app.get("/health")
async def health_check():
    """Health check with model status"""
    chat_service = get_chat_service()
    is_ready = (
        chat_service.embedding_model is not None and 
        chat_service.chain is not None and 
        chat_service.hyde_transformer is not None
    )
    
    return {
        "status": "healthy" if is_ready else "initializing",
        "models_loaded": is_ready,
        "services": {
            "embedding_model": chat_service.embedding_model is not None,
            "chain": chat_service.chain is not None,
            "hyde_transformer": chat_service.hyde_transformer is not None
        }
    }


@app.get("/ready")
async def readiness_check():
    """Check if all models are loaded and ready"""
    chat_service = get_chat_service()
    is_ready = (
        chat_service.embedding_model is not None and 
        chat_service.chain is not None and 
        chat_service.hyde_transformer is not None
    )
    
    if is_ready:
        return {"status": "ready", "message": "All models loaded successfully"}
    else:
        return {"status": "not_ready", "message": "Models are still loading..."}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
