"""
Ultra Fast RAG Service - Minimal startup time for development
"""
import time
import os
from typing import Dict, Any, AsyncGenerator, List
from pathlib import Path

from backend.models.chat_models import ChatMessage
from ragbase.config import Config
from ragbase.model import create_llm

class UltraFastService:
    """Ultra lightweight service with instant startup"""
    
    def __init__(self):
        self.llm = None
        self.mock_responses = [
            "Tôi hiểu bạn đang gặp khó khăn. Hãy chia sẻ thêm về tình huống của bạn.",
            "Điều đó nghe có vẻ căng thẳng. Bạn đã thử các phương pháp thư giãn nào chưa?",
            "Tôi nghĩ việc tìm kiếm sự hỗ trợ chuyên nghiệp sẽ rất có ích cho bạn.",
            "Có vẻ như bạn đang trải qua một thời gian khó khăn. Hãy nhớ rằng mọi thứ sẽ tốt lên.",
            "Việc chăm sóc bản thân là rất quan trọng. Bạn có thể bắt đầu với những hoạt động nhỏ."
        ]
        self.response_index = 0
    
    @classmethod
    async def create(cls) -> "UltraFastService":
        """Instant initialization"""
        service = cls()
        await service._init()
        return service
    
    async def _init(self):
        """Ultra fast initialization - under 1 second"""
        print("⚡ Ultra Fast Mode - Instant startup...")
        start = time.time()
        
        # Only create LLM for basic responses
        self.llm = create_llm()
        
        end = time.time()
        print(f"✅ Ultra Fast service ready in {end - start:.2f} seconds")
    
    async def process_message(
        self,
        message: str,
        chat_id: str,
        chat_history: List[ChatMessage]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message with instant mock response"""
        
        # Simple keyword-based responses
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['buồn', 'sad', 'depression', 'trầm cảm']):
            response = "Tôi hiểu bạn đang cảm thấy buồn. Việc chia sẻ cảm xúc là bước đầu quan trọng để cải thiện tâm trạng."
        elif any(word in message_lower for word in ['lo âu', 'anxiety', 'lo lắng', 'stress']):
            response = "Lo âu là cảm xúc bình thường, nhưng nếu kéo dài có thể ảnh hưởng đến cuộc sống. Hãy thử các kỹ thuật thở sâu."
        elif any(word in message_lower for word in ['mất ngủ', 'insomnia', 'không ngủ được']):
            response = "Mất ngủ có thể do nhiều nguyên nhân. Hãy tạo thói quen ngủ đều đặn và tránh màn hình trước khi ngủ."
        else:
            # Rotate through mock responses
            response = self.mock_responses[self.response_index % len(self.mock_responses)]
            self.response_index += 1
        
        # Simulate streaming response
        words = response.split()
        current_text = ""
        
        for word in words:
            current_text += word + " "
            yield {
                "type": "content",
                "content": current_text.strip()
            }
            # Small delay to simulate streaming
            import asyncio
            await asyncio.sleep(0.1)
        
        yield {
            "type": "done",
            "content": current_text.strip()
        }
