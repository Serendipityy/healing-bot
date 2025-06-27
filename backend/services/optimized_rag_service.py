"""
Optimized RAG service with progressive loading and caching
"""
import asyncio
import pickle
import time
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, List, Optional
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from backend.models.chat_models import ChatMessage
from ragbase.chain import create_chain
from ragbase.config import Config
from ragbase.model import create_embeddings, create_llm
from ragbase.utils import load_summary_documents_from_excel

class OptimizedRAGService:
    """RAG service with caching and progressive loading"""
    
    def __init__(self):
        self.chain = None
        self.client = None
        self.embedding_model = None
        self.llm = None
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    @classmethod
    async def create(cls) -> "OptimizedRAGService":
        """Factory method with optimized initialization"""
        service = cls()
        await service._optimized_init()
        return service
    
    async def _optimized_init(self):
        """Optimized initialization with caching and minimal components"""
        print("🚀 Optimized RAG service - Smart loading...")
        start_total = time.time()
        
        # Step 1: Quick essentials
        print("  📡 Connecting to Qdrant...")
        self.client = QdrantClient(host="localhost", port=6333, timeout=300)
        
        print("  🤖 Loading LLM...")
        self.llm = create_llm()
        
        # Step 2: Load embedding model with caching
        embedding_cache = self.cache_dir / "embedding_model.pkl"
        if embedding_cache.exists():
            print("  📊 Loading cached embedding model...")
            try:
                with open(embedding_cache, 'rb') as f:
                    self.embedding_model = pickle.load(f)
                print("    ✅ Cached embedding model loaded")
            except Exception as e:
                print(f"    ⚠️ Cache failed, loading fresh: {e}")
                self.embedding_model = await self._load_fresh_embeddings()
        else:
            self.embedding_model = await self._load_fresh_embeddings()
        
        # Step 3: Initialize with SUMMARY data only (much smaller)
        print("  📚 Loading summary documents only...")
        step_start = time.time()
        
        # Use summary file only - it's smaller and faster
        summary_documents = load_summary_documents_from_excel(Config.Path.SUMMARY_EXCEL_FILE)
        step_time = time.time() - step_start
        print(f"    ✅ Summary documents loaded in {step_time:.2f}s ({len(summary_documents)} docs)")
        
        # Step 4: Create minimal vector store
        print("  🗄️ Setting up vector store...")
        step_start = time.time()
        summary_vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="summary",
            embedding=self.embedding_model
        )
        step_time = time.time() - step_start
        print(f"    ✅ Vector store ready in {step_time:.2f}s")
        
        # Step 5: Create lightweight chain (no rerankers for speed)
        print("  ⛓️ Building lightweight chain...")
        step_start = time.time()
        
        # Simple retriever without reranking for speed
        from ragbase.retriever import create_hybrid_retriever
        retriever = create_hybrid_retriever(self.llm, summary_documents, summary_vector_store)
        
        # Skip rerankers in optimized mode
        self.chain = create_chain(self.llm, retriever, retriever)
        
        step_time = time.time() - step_start
        print(f"    ✅ Lightweight chain built in {step_time:.2f}s")
        
        total_time = time.time() - start_total
        print(f"✅ Optimized RAG service ready in {total_time:.2f} seconds")
        print("💡 Using summary data only for fast responses")
    
    async def _load_fresh_embeddings(self):
        """Load embedding model and cache it"""
        print("  📊 Loading fresh embedding model...")
        step_start = time.time()
        
        # Load in thread to avoid blocking
        loop = asyncio.get_event_loop()
        embedding_model = await loop.run_in_executor(None, create_embeddings)
        
        # Cache for next time
        try:
            embedding_cache = self.cache_dir / "embedding_model.pkl"
            with open(embedding_cache, 'wb') as f:
                pickle.dump(embedding_model, f)
            print("    💾 Embedding model cached for next startup")
        except Exception as e:
            print(f"    ⚠️ Caching failed: {e}")
        
        step_time = time.time() - step_start
        print(f"    ✅ Fresh embedding model loaded in {step_time:.2f}s")
        return embedding_model
    
    async def process_message(
        self,
        message: str,
        chat_id: str,
        chat_history: List[ChatMessage]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message using optimized chain"""
        if not self.chain:
            yield {
                "type": "error",
                "content": "Service not initialized"
            }
            return
        
        try:
            # Convert chat history to the format expected by the chain
            history_text = ""
            for msg in chat_history[-5:]:  # Only last 5 messages for speed
                role = "Human" if msg.role == "user" else "Assistant"
                history_text += f"{role}: {msg.content}\n"
            
            # Use the chain to get response
            from ragbase.chain import ask_question
            
            async for chunk in ask_question(
                self.chain,
                message,
                chat_id  # Use chat_id as session_id
            ):
                # Handle different types of data from ask_question
                if isinstance(chunk, str):
                    # This is actual content from LLM
                    yield {
                        "type": "content",
                        "content": chunk
                    }
                elif isinstance(chunk, list):
                    # This is retrieval results, skip for streaming
                    pass
                else:
                    # Convert other types to string
                    yield {
                        "type": "content",
                        "content": str(chunk)
                    }
            
            yield {
                "type": "done"
            }
            
        except Exception as e:
            print(f"Error in optimized processing: {e}")
            yield {
                "type": "error", 
                "content": f"Processing error: {str(e)}"
            }
