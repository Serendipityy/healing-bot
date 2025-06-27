"""
RAG service for processing messages and retrieving context
"""
import re
import time
from typing import List, Dict, Any, AsyncGenerator
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

class RAGService:
    def __init__(self):
        self.chain = None
        self.query_transformer = None
        self.client = None
        self.embedding_model = None
        self.llm = None
    
    @classmethod
    async def create(cls) -> "RAGService":
        """Factory method to create and initialize RAGService"""
        service = cls()
        await service._initialize()
        return service
    
    async def _initialize(self):
        """Initialize all RAG components with optimization"""
        print("🔧 Initializing RAG service...")
        start_total = time.time()
        
        # Step 1: Initialize basic components (fast)
        print("  📡 Connecting to Qdrant...")
        self.client = QdrantClient(host="localhost", port=6333, timeout=300)
        
        print("  🤖 Loading language model...")
        self.llm = create_llm()
        
        print("  🔍 Initializing query transformer...")
        self.query_transformer = QueryTransformationHyDE()
        
        # Step 2: Load embedding model (slowest part)
        print("  📊 Loading embedding model (this takes the longest)...")
        step_start = time.time()
        self.embedding_model = create_embeddings()
        step_time = time.time() - step_start
        print(f"    ✅ Embedding model loaded in {step_time:.2f}s")
        
        # Step 3: Load documents in parallel (if possible)
        print("  📚 Loading documents...")
        step_start = time.time()
        
        # Try to load documents concurrently
        import asyncio
        async def load_docs():
            loop = asyncio.get_event_loop()
            # Run in thread pool to avoid blocking
            docs_task = loop.run_in_executor(None, load_documents_from_excel, Config.Path.EXCEL_FILE)
            summary_task = loop.run_in_executor(None, load_summary_documents_from_excel, Config.Path.SUMMARY_EXCEL_FILE)
            return await asyncio.gather(docs_task, summary_task)
        
        try:
            documents, summary_documents = await load_docs()
        except Exception as e:
            print(f"    ⚠️ Async loading failed, falling back to sync: {e}")
            documents = load_documents_from_excel(excel_path=Config.Path.EXCEL_FILE)
            summary_documents = load_summary_documents_from_excel(excel_path=Config.Path.SUMMARY_EXCEL_FILE)
        
        step_time = time.time() - step_start
        print(f"    ✅ Documents loaded in {step_time:.2f}s")
        
        # Step 4: Initialize vector stores
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
        print("  🔍 Creating retrievers...")
        step_start = time.time()
        retriever_full = create_hybrid_retriever(self.llm, documents, vector_store)
        retriever_summary = create_hybrid_retriever(self.llm, summary_documents, summary_vector_store)
        step_time = time.time() - step_start
        print(f"    ✅ Retrievers created in {step_time:.2f}s")
        
        # Step 6: Apply compression (optional and slow)
        if Config.Retriever.USE_RERANKER:
            print("  🎯 Applying reranker...")
            step_start = time.time()
            retriever_full = ContextualCompressionRetriever(
                base_compressor=create_reranker(),
                base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=create_reranker(),
                base_retriever=retriever_summary
            )
            step_time = time.time() - step_start
            print(f"    ✅ Reranker applied in {step_time:.2f}s")
        
        if Config.Retriever.USE_CHAIN_FILTER:
            print("  🔧 Applying chain filter...")
            step_start = time.time()
            retriever_full = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(self.llm),
                base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(self.llm),
                base_retriever=retriever_summary
            )
            step_time = time.time() - step_start
            print(f"    ✅ Chain filter applied in {step_time:.2f}s")
        
        # Step 7: Create the final chain
        print("  ⛓️ Building final chain...")
        step_start = time.time()
        self.chain = create_chain(self.llm, retriever_full, retriever_summary)
        step_time = time.time() - step_start
        print(f"    ✅ Chain built in {step_time:.2f}s")
        
        total_time = time.time() - start_total
        print(f"✅ RAG service initialized in {total_time:.2f} seconds")
    
    async def process_message(
        self,
        message: str,
        chat_id: str,
        chat_history: List[ChatMessage]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message and generate streaming response"""
        
        if not self.chain:
            yield {"type": "error", "content": "RAG service not initialized"}
            return
        
        try:
            # Prepare context from chat history
            history_context = []
            for msg in chat_history[-5:]:  # Use last 5 messages for context
                if msg.role == "user":
                    history_context.append(msg.content)
            
            # Transform the query with context
            context_question = "\n".join(history_context + [message])
            transformed_question = self.query_transformer.transform_query(context_question)
            
            # Stream the response
            full_response = ""
            documents = []
            
            async for event in ask_question(
                self.chain, 
                transformed_question, 
                session_id=chat_id
            ):
                if isinstance(event, str):
                    # Content streaming
                    full_response += event
                    yield {
                        "type": "content",
                        "content": event
                    }
                elif isinstance(event, list):
                    # Documents retrieved
                    documents.extend(event)
                    yield {
                        "type": "documents",
                        "documents": [
                            {
                                "content": doc.page_content,
                                "metadata": doc.metadata
                            }
                            for doc in event
                        ]
                    }
            
            # Clean up the response (remove <think> tags)
            clean_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
            
            # Signal completion
            yield {
                "type": "complete",
                "full_response": clean_response.strip(),
                "documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in documents
                ]
            }
            
        except Exception as e:
            print(f"❌ Error in RAG processing: {e}")
            yield {
                "type": "error",
                "content": f"Xin lỗi, mình đang gặp vấn đề kỹ thuật: {str(e)}"
            }
    
    async def close(self):
        """Clean up resources"""
        if self.client:
            self.client.close()
        print("🛑 RAG service closed")
