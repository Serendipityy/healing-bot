"""
Production Optimized RAG Service - Excellent quality with smart optimizations
"""
import asyncio
import pickle
import time
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, List
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import LLMChainFilter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from backend.models.chat_models import ChatMessage
from ragbase.chain import create_chain, ask_question
from ragbase.config import Config
from ragbase.hyde import QueryTransformationHyDE
from ragbase.model import create_embeddings, create_llm, create_reranker
from ragbase.retriever import create_hybrid_retriever
from ragbase.utils import load_documents_from_excel, load_summary_documents_from_excel

class ProductionRAGService:
    """Production-ready RAG service with excellent quality and smart caching"""
    
    def __init__(self):
        self.chain = None
        self.query_transformer = None
        self.client = None
        self.embedding_model = None
        self.llm = None
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    @classmethod
    async def create(cls) -> "ProductionRAGService":
        """Factory method with production optimizations"""
        service = cls()
        await service._production_init()
        return service
    
    async def _production_init(self):
        """Production initialization with all features + smart caching"""
        print("🚀 Production RAG service - Excellent quality with optimizations...")
        start_total = time.time()
        
        # Step 1: Essential components (parallel where possible)
        print("  📡 Initializing core components...")
        step_start = time.time()
        
        # Initialize in parallel
        async def init_core():
            self.client = QdrantClient(host="localhost", port=6333, timeout=300, prefer_grpc=False)
            self.llm = create_llm()
            self.query_transformer = QueryTransformationHyDE()
        
        await init_core()
        step_time = time.time() - step_start
        print(f"    ✅ Core components ready in {step_time:.2f}s")
        
        # Step 2: Load embedding model with smart caching
        print("  📊 Loading embedding model...")
        step_start = time.time()
        self.embedding_model = await self._get_cached_embeddings()
        step_time = time.time() - step_start
        print(f"    ✅ Embedding model ready in {step_time:.2f}s")
        
        # Step 3: Load documents in parallel
        print("  📚 Loading documents (parallel)...")
        step_start = time.time()
        
        async def load_docs_parallel():
            loop = asyncio.get_event_loop()
            # Run both loads in parallel
            docs_task = loop.run_in_executor(None, load_documents_from_excel, Config.Path.EXCEL_FILE)
            summary_task = loop.run_in_executor(None, load_summary_documents_from_excel, Config.Path.SUMMARY_EXCEL_FILE)
            return await asyncio.gather(docs_task, summary_task)
        
        documents, summary_documents = await load_docs_parallel()
        step_time = time.time() - step_start
        print(f"    ✅ Documents loaded in {step_time:.2f}s ({len(documents)} full + {len(summary_documents)} summary)")
        
        # Step 4: Setup vector stores in parallel
        print("  🗄️ Setting up vector stores...")
        step_start = time.time()
        
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="documents",
            embedding=self.embedding_model
        )
        summary_vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="summary",
            embedding=self.embedding_model
        )
        
        step_time = time.time() - step_start
        print(f"    ✅ Vector stores ready in {step_time:.2f}s")
        
        # Step 5: Create retrievers
        print("  🔍 Creating hybrid retrievers...")
        step_start = time.time()
        
        retriever_full = create_hybrid_retriever(self.llm, documents, vector_store)
        retriever_summary = create_hybrid_retriever(self.llm, summary_documents, summary_vector_store)
        
        step_time = time.time() - step_start
        print(f"    ✅ Retrievers created in {step_time:.2f}s")
        
        # Step 6: Apply production-quality enhancements
        print("  🎯 Applying quality enhancements...")
        step_start = time.time()
        
        # Apply reranker for better quality
        if Config.Retriever.USE_RERANKER:
            reranker = create_reranker()
            retriever_full = ContextualCompressionRetriever(
                base_compressor=reranker,
                base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=reranker,
                base_retriever=retriever_summary
            )
            print("    ✅ Reranker applied for better relevance")
        
        # Apply chain filter for highest quality
        if Config.Retriever.USE_CHAIN_FILTER:
            retriever_full = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(self.llm),
                base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(self.llm),
                base_retriever=retriever_summary
            )
            print("    ✅ Chain filter applied for highest quality")
        
        step_time = time.time() - step_start
        print(f"    ✅ Quality enhancements applied in {step_time:.2f}s")
        
        # Step 7: Create production chain
        print("  ⛓️ Building production chain...")
        step_start = time.time()
        self.chain = create_chain(self.llm, retriever_full, retriever_summary)
        step_time = time.time() - step_start
        print(f"    ✅ Production chain built in {step_time:.2f}s")
        
        total_time = time.time() - start_total
        print(f"✅ Production RAG service ready in {total_time:.2f} seconds")
        print("🏆 Excellent quality mode: Full+Summary data, Reranker, Chain filter")
    
    async def _get_cached_embeddings(self):
        """Get embedding model with smart caching"""
        embedding_cache = self.cache_dir / "embedding_model.pkl"
        
        if embedding_cache.exists():
            try:
                print("    💾 Loading from cache...")
                with open(embedding_cache, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"    ⚠️ Cache corrupted, reloading: {e}")
        
        # Load fresh and cache
        print("    🔄 Loading fresh model...")
        loop = asyncio.get_event_loop()
        embedding_model = await loop.run_in_executor(None, create_embeddings)
        
        # Cache for next time
        try:
            with open(embedding_cache, 'wb') as f:
                pickle.dump(embedding_model, f)
            print("    💾 Cached for next startup")
        except Exception as e:
            print(f"    ⚠️ Caching failed: {e}")
        
        return embedding_model
    
    async def process_message(
        self,
        message: str,
        chat_id: str,
        chat_history: List[ChatMessage]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message with excellent quality and chat history"""
        if not self.chain:
            yield {"type": "error", "content": "Service not initialized"}
            return
        
        try:
            # Transform query for better retrieval (sync call)
            transformed_question = self.query_transformer.transform_query(message)
            
            # Build context from chat history
            history_context = ""
            if chat_history:
                recent_history = chat_history[-10:]  # Last 10 messages for context
                for msg in recent_history:
                    role = "Human" if msg.role == "user" else "Assistant"
                    history_context += f"{role}: {msg.content}\n"
                
                # Add current question with context
                full_question = f"Chat History:\n{history_context}\nCurrent Question: {transformed_question}"
                
                # 🔍 DEBUG: Print context being used
                print(f"\n{'='*60}")
                print(f"🔍 CHAT CONTEXT DEBUG")
                print(f"{'='*60}")
                print(f"📝 Original Question: {message}")
                print(f"🔄 Transformed Question: {transformed_question}")
                print(f"📚 Chat History ({len(recent_history)} messages):")
                for i, msg in enumerate(recent_history, 1):
                    print(f"  {i}. [{msg.role.upper()}]: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
                print(f"🎯 Full Context Question:")
                print(f"{full_question}")
                print(f"{'='*60}\n")
            else:
                full_question = transformed_question
                print(f"\n🔍 NO CHAT HISTORY - Using direct question: {transformed_question}\n")
            
            # Stream response with excellent quality
            async for event in ask_question(self.chain, full_question, chat_id):
                if isinstance(event, str):
                    # Content chunk
                    yield {
                        "type": "content",
                        "content": event
                    }
                elif isinstance(event, list):
                    # Documents (skip for streaming)
                    continue
            
            yield {"type": "done"}
            
        except Exception as e:
            print(f"Error in production processing: {e}")
            yield {
                "type": "error", 
                "content": f"Processing error: {str(e)}"
            }
