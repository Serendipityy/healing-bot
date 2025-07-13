"""
Chat service for handling AI processing and streaming responses.
"""

import asyncio
import os
import re
import sys
import time
import json
from typing import AsyncGenerator, List, Optional

import numpy as np
from dotenv import load_dotenv
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import LLMChainFilter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ragbase.chain import ask_question, create_chain
from ragbase.config import Config
from ragbase.hyde import QueryTransformationHyDE
from ragbase.model import create_embeddings, create_llm, create_reranker
from ragbase.retriever import create_optimized_retriever
from ragbase.session_history import add_message_to_history

from backend.models import ChatRequest, StreamChunk

load_dotenv()


class ChatService:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.client = QdrantClient(host="localhost", port=6333, timeout=300)
            self.embedding_model = None
            self.chain = None
            self.hyde_transformer = None
            self._initialize()
            ChatService._initialized = True
    
    def _initialize(self):
        """Initialize all required components"""
        print("🚀 Initializing ChatService...")
        start = time.time()
        
        print("📚 Loading embedding model...")
        # Initialize embedding model
        self.embedding_model = create_embeddings()
        print("✅ Embedding model loaded")
        
        print("🗃️ Connecting to vector stores...")
        # Initialize vector stores
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
        print("✅ Vector stores connected")
        
        print("🤖 Loading LLM...")
        # Initialize LLM
        llm = create_llm()
        print("✅ LLM loaded")
        
        print("🔍 Setting up retrievers...")
        # Create optimized retrievers
        retriever_full = create_optimized_retriever(llm, vector_store, "full")
        retriever_summary = create_optimized_retriever(llm, summary_vector_store, "summary")
        
        # Apply reranker or chain filter if needed
        if Config.Retriever.USE_RERANKER:
            print("🎯 Applying reranker...")
            retriever_full = ContextualCompressionRetriever(
                base_compressor=create_reranker(), base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=create_reranker(), base_retriever=retriever_summary
            )
        
        if Config.Retriever.USE_CHAIN_FILTER:
            print("🔗 Applying chain filter...")
            retriever_full = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_summary
            )
        print("✅ Retrievers configured")
        
        print("⛓️ Creating chain...")
        # Create chain
        self.chain = create_chain(llm, retriever_full, retriever_summary)
        print("✅ Chain created")
        
        print("🔄 Initializing HyDE transformer...")
        # Initialize HyDE transformer
        self.hyde_transformer = QueryTransformationHyDE()
        print("✅ HyDE transformer ready")
        
        end = time.time()
        print(f"⚡ ChatService initialized in: {end - start:.2f} seconds")
        print("🎉 Ready to process chat requests!")
    
    async def process_message_stream(
        self, 
        request: ChatRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Process message and yield streaming response"""
        try:
            # Transform query with HyDE
            hyde_start = time.time()
            question_transformed = self.hyde_transformer.transform_query(
                request.message, 
                fast_mode=True
            )
            hyde_end = time.time()
            print(f"⚡ HyDE took: {hyde_end - hyde_start:.2f}s")
            
            # Use session_id or conversation_id
            session_id = request.session_id or request.conversation_id or "temp_session"
            
            full_response = ""
            documents = []
            
            # Stream response from chain
            async for event in ask_question(self.chain, question_transformed, session_id=session_id):
                if isinstance(event, str) and event.strip():
                    # Remove thinking tags before yielding
                    clean_event = re.sub(r"<think>.*?</think>", "", event, flags=re.DOTALL)
                    if clean_event.strip():
                        full_response += clean_event
                        yield StreamChunk(
                            type="token",
                            content=clean_event,
                            conversation_id=request.conversation_id
                        )
                
                elif isinstance(event, list):
                    documents.extend(event)
            
            # Yield sources if available
            if documents:
                sources = []
                for doc in documents[:3]:
                    # Clean metadata to avoid numpy serialization issues
                    metadata = {}
                    if hasattr(doc, 'metadata') and doc.metadata:
                        for key, value in doc.metadata.items():
                            # Convert numpy types to Python types
                            if isinstance(value, (np.integer, np.floating)):
                                metadata[key] = value.item()
                            elif isinstance(value, np.ndarray):
                                metadata[key] = value.tolist()
                            else:
                                metadata[key] = value
                    
                    sources.append({
                        "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                        "metadata": metadata
                    })
                
                yield StreamChunk(
                    type="sources",
                    content="",
                    conversation_id=request.conversation_id,
                    sources=sources
                )
            
            # Save message to history if conversation_id exists
            if request.conversation_id and request.conversation_id != "temp_session":
                # Clean final response
                final_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
                add_message_to_history(request.conversation_id, "assistant", final_response)
            
            # End stream
            yield StreamChunk(
                type="end",
                content="",
                conversation_id=request.conversation_id
            )
            
        except Exception as e:
            print(f"Error in process_message_stream: {e}")
            yield StreamChunk(
                type="error",
                content=f"Xin lỗi, mình đang gặp vấn đề kỹ thuật: {str(e)}",
                conversation_id=request.conversation_id
            )


# Global service instance
chat_service = None

def get_chat_service() -> ChatService:
    """Get or create chat service instance"""
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service
