"""
FastAPI Backend for Healing Bot
Handles all async operations and RAG processing
"""
import os
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import asyncio
import datetime
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from backend.models.chat_models import (
    ChatRequest, 
    ChatResponse, 
    ChatHistory, 
    CreateChatRequest,
    DeleteChatRequest
)
from backend.services.chat_service import ChatService
from backend.services.rag_service import RAGService
from backend.services.fast_rag_service import FastRAGService
from backend.config.settings import get_settings

# Global services
chat_service: Optional[ChatService] = None
rag_service: Optional[RAGService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global chat_service, rag_service
    
    # Check mode from environment
    mode = os.getenv("RAG_MODE", "production").lower()
    
    # Initialize chat service
    chat_service = ChatService()
    
    if mode == "production":
        print("🏆 PRODUCTION MODE - excellent quality with smart optimizations")
        from backend.services.production_rag_service import ProductionRAGService
        rag_service = await ProductionRAGService.create()
    elif mode == "ultra":
        print("⚡ ULTRA FAST MODE - instant startup with mock responses")
        from backend.services.ultra_fast_service import UltraFastService
        rag_service = await UltraFastService.create()
    elif mode == "optimized":
        print("🚀 OPTIMIZED MODE - smart caching and minimal components")
        from backend.services.optimized_rag_service import OptimizedRAGService
        rag_service = await OptimizedRAGService.create()
    elif mode == "fast":
        print("⚡ FAST MODE - lightweight RAG service")
        rag_service = await FastRAGService.create()
    else:
        print("🔧 FULL MODE - complete RAG service")
        rag_service = await RAGService.create()
    
    print("🚀 Backend services initialized")
    yield
    
    # Cleanup on shutdown
    if chat_service:
        await chat_service.close()
    if rag_service:
        await rag_service.close()
    print("🛑 Backend services shut down")

# Create FastAPI app
app = FastAPI(
    title="Healing Bot Backend",
    description="Backend API for Healing Bot RAG system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/chat/create")
async def create_chat(request: CreateChatRequest) -> Dict[str, str]:
    """Create a new chat session"""
    chat_id = await chat_service.create_chat(request.initial_message)
    return {"chat_id": chat_id}

@app.post("/chat/{chat_id}/message")
async def send_message(chat_id: str, request: ChatRequest):
    """Send a message and get streaming response"""
    
    async def generate_response():
        try:
            full_response = ""
            documents = []
            
            async for chunk in rag_service.process_message(
                message=request.message,
                chat_id=chat_id,
                chat_history=request.chat_history or []
            ):
                if chunk.get("type") == "content":
                    content = chunk.get('content', '')
                    full_response += content
                    yield f"data: {content}\n\n"
                elif chunk.get("type") == "documents":
                    documents.extend(chunk.get('documents', []))
                elif chunk.get("type") == "complete":
                    # Save the complete response
                    await chat_service.save_message(
                        chat_id=chat_id,
                        role="user",
                        content=request.message
                    )
                    await chat_service.save_message(
                        chat_id=chat_id,
                        role="assistant", 
                        content=chunk.get("full_response", full_response)
                    )
                    yield f"event: complete\ndata: Response complete\n\n"
                    break
                    
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        generate_response(), 
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/chat/{chat_id}/history")
async def get_chat_history(chat_id: str) -> ChatHistory:
    """Get chat history for a specific chat"""
    history = await chat_service.get_chat_history(chat_id)
    if not history:
        raise HTTPException(status_code=404, detail="Chat not found")
    return history

@app.get("/chats")
async def get_all_chats() -> List[ChatHistory]:
    """Get all chat sessions"""
    return await chat_service.get_all_chats()

@app.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat session"""
    success = await chat_service.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"message": "Chat deleted successfully"}

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
