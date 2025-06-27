"""
Fast RAG Service for Development - Optimized for speed
"""
import time
from typing import Dict, Any, AsyncGenerator
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from backend.models.chat_models import ChatMessage
from ragbase.chain import create_chain
from ragbase.config import Config
from ragbase.model import create_embeddings, create_llm
from ragbase.utils import load_documents_from_excel, load_summary_documents_from_excel

class FastRAGService:
    """Lightweight RAG service with minimal initialization for development"""
    
    def __init__(self):
        self.chain = None
        self.client = None
        self.embedding_model = None
        self.llm = None
        self._initialized = False
    
    @classmethod
    async def create(cls) -> "FastRAGService":
        """Factory method with lazy initialization"""
        service = cls()
        await service._quick_init()
        return service
    
    async def _quick_init(self):
        """Quick initialization - only essential components"""
        print("⚡ Fast RAG service - Quick initialization...")
        start = time.time()
        
        # Only initialize what's absolutely necessary
        self.client = QdrantClient(host="localhost", port=6333, timeout=300)
        self.llm = create_llm()
        
        end = time.time()
        print(f"✅ Fast RAG ready in {end - start:.2f} seconds (lazy loading enabled)")
        self._initialized = True
    
    async def _ensure_full_init(self):
        """Lazy load full components when first needed"""
        if hasattr(self, '_full_initialized'):
            return
            
        print("🔄 Loading full RAG components (first use)...")
        start = time.time()
        
        # Load embedding model
        self.embedding_model = create_embeddings()
        
        # Load documents (only summary for speed)
        summary_documents = load_summary_documents_from_excel(excel_path=Config.Path.SUMMARY_EXCEL_FILE)
        
        # Use only summary vector store for speed
        summary_vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="summary",
            embedding=self.embedding_model
        )
        
        # Create simplified chain (summary only)
        from ragbase.retriever import create_hybrid_retriever
        retriever_summary = create_hybrid_retriever(self.llm, summary_documents, summary_vector_store)
        
        # Use summary retriever for both (faster)
        self.chain = create_chain(self.llm, retriever_summary, retriever_summary)
        
        end = time.time()
        print(f"✅ Full components loaded in {end - start:.2f} seconds")
        self._full_initialized = True
    
    async def process_message(
        self,
        message: str,
        chat_id: str,
        chat_history: list[ChatMessage]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message with lazy loading"""
        
        if not self._initialized:
            yield {"type": "error", "content": "Service not initialized"}
            return
        
        # Lazy load full components on first use
        await self._ensure_full_init()
        
        if not self.chain:
            yield {"type": "error", "content": "RAG chain not available"}
            return
        
        try:
            # Simplified processing
            from ragbase.hyde import QueryTransformationHyDE
            from ragbase.chain import ask_question
            
            # Quick query transformation
            transformer = QueryTransformationHyDE()
            transformed_question = transformer.transform_query(message)
            
            # Stream response
            full_response = ""
            documents = []
            
            async for event in ask_question(self.chain, transformed_question, session_id=chat_id):
                if isinstance(event, str):
                    full_response += event
                    yield {"type": "content", "content": event}
                elif isinstance(event, list):
                    documents.extend(event)
                    yield {
                        "type": "documents",
                        "documents": [
                            {"content": doc.page_content, "metadata": doc.metadata}
                            for doc in event
                        ]
                    }
            
            # Clean response
            import re
            clean_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
            
            yield {
                "type": "complete",
                "full_response": clean_response.strip(),
                "documents": [
                    {"content": doc.page_content, "metadata": doc.metadata}
                    for doc in documents
                ]
            }
            
        except Exception as e:
            print(f"❌ Error in fast RAG processing: {e}")
            yield {"type": "error", "content": f"Lỗi xử lý: {str(e)}"}
    
    async def close(self):
        """Clean up resources"""
        if self.client:
            self.client.close()
        print("🛑 Fast RAG service closed")
