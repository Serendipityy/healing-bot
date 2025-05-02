import ast
import logging
from pathlib import Path
from typing import List

import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_experimental.text_splitter import SemanticChunker
from langchain_qdrant import Qdrant
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ragbase.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def safe_parse_answers(x):
    try:
        if isinstance(x, str):
            # Giữ lại \n nhưng escape đúng để literal_eval hiểu được
            escaped = x.encode('unicode_escape').decode('utf-8')
            return ast.literal_eval(escaped)
        return x
    except Exception as e:
        print(f"[!] Lỗi khi parse: {x} -> {e}")
        return []

# Huggingface Embeddings model
class Ingestor:
    def __init__(self):
        # self.embeddings = FastEmbedEmbeddings(model_name=Config.Model.EMBEDDINGS)
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.Model.EMBEDDINGS)
        self.semantic_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=0.95,  
        )
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2048,
            chunk_overlap=128,
            add_start_index=True,
        )

    def ingest(self, documents: list[Document] = None) -> VectorStore:
        if documents:
            # Split documents
            logging.info("Splitting documents...")
            split_docs = self.recursive_splitter.split_documents(
                self.semantic_splitter.create_documents([doc.page_content for doc in documents])
            )
            
            # Add metadata back
            logging.info("Adding metadata back...")
            for split_doc in split_docs:
                split_doc.metadata = documents[0].metadata
            
            # Create vector store
            logging.info("Creating vector store...")
            return Qdrant.from_documents(
                documents=split_docs,
                embedding=self.embeddings,
                path=Config.Path.DATABASE_DIR,
                collection_name=Config.Database.DOCUMENTS_COLLECTION,
            )
        else:
            # Load existing vector store
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.DOCUMENTS_COLLECTION,
                path=Config.Path.DATABASE_DIR,
            )

