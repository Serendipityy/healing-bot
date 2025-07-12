from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..models.chat import Conversation, ConversationCreate
from ..services.conversation_service import get_conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("/", response_model=dict)
async def create_conversation(request: ConversationCreate):
    """Create a new conversation"""
    try:
        conversation_service = get_conversation_service()
        conversation_id = conversation_service.create_conversation(request.title)
        
        return {
            "id": conversation_id,
            "title": request.title or "New Conversation",
            "message": "Conversation created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[dict])
async def get_all_conversations():
    """Get all conversations"""
    try:
        conversation_service = get_conversation_service()
        return conversation_service.get_all_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    try:
        conversation_service = get_conversation_service()
        conversation = conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}/title", response_model=dict)
async def update_conversation_title(conversation_id: str, title: str):
    """Update conversation title"""
    try:
        conversation_service = get_conversation_service()
        success = conversation_service.update_conversation_title(conversation_id, title)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}", response_model=dict)
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        conversation_service = get_conversation_service()
        success = conversation_service.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/messages", response_model=List[dict])
async def get_conversation_messages(conversation_id: str):
    """Get messages for a conversation"""
    try:
        conversation_service = get_conversation_service()
        messages = conversation_service.get_conversation_messages(conversation_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
