import datetime
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models.chat import ChatRequest, ChatResponse, StreamChunk
from ..services.chat_service import get_chat_service
from ..services.conversation_service import get_conversation_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response"""
    try:
        chat_service = get_chat_service()
        conversation_service = get_conversation_service()
        
        # Create conversation if not exists
        if not request.conversation_id:
            request.conversation_id = conversation_service.create_conversation()
            
            # Save initial assistant message
            conversation_service.save_message(
                request.conversation_id,
                "assistant",
                "Xin chào! Mình ở đây sẵn sàng lắng nghe và chia sẻ cùng bạn. Bạn đang nghĩ gì vậy?"
            )
        
        # Save user message
        conversation_service.save_message(
            request.conversation_id,
            "user",
            request.message
        )
        
        # Update title if first user message
        messages = conversation_service.get_conversation_messages(request.conversation_id)
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if len(user_messages) == 1:
            title = _format_conversation_title(request.message)
            conversation_service.update_conversation_title(request.conversation_id, title)
        
        async def generate():
            async for chunk in chat_service.process_message_stream(request):
                try:
                    # Convert to dict and handle numpy types
                    chunk_data = chunk.model_dump()
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                except Exception as e:
                    # Fallback for serialization errors
                    error_chunk = {
                        "type": "error", 
                        "content": f"Serialization error: {str(e)}",
                        "conversation_id": request.conversation_id
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """Non-streaming chat endpoint"""
    try:
        chat_service = get_chat_service()
        conversation_service = get_conversation_service()
        
        # Create conversation if not exists
        if not request.conversation_id:
            request.conversation_id = conversation_service.create_conversation()
        
        # Save user message
        conversation_service.save_message(
            request.conversation_id,
            "user",
            request.message
        )
        
        # Collect streaming response
        full_response = ""
        sources = []
        
        async for chunk in chat_service.process_message_stream(request):
            if chunk.type == "token":
                full_response += chunk.content
            elif chunk.type == "sources":
                sources = chunk.sources
            elif chunk.type == "error":
                raise HTTPException(status_code=500, detail=chunk.content)
        
        return ChatResponse(
            response=full_response,
            conversation_id=request.conversation_id,
            sources=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_conversation_title(text: str, max_length: int = 30) -> str:
    """Format conversation title with max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."
