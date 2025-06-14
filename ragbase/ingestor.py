import ast
import logging
import os
from pathlib import Path
from typing import List

import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_experimental.text_splitter import SemanticChunker
from langchain_qdrant import Qdrant
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ragbase.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")



# Huggingface Embeddings model
class Ingestor:
    def __init__(self):
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
    def ingest(self, documents: list[Document] = None, chunk_size: int = 1000, resume: bool = True) -> None:
        """
        Ingest documents into the vector store, processing them in chunks.
        
        Args:
            documents (list[Document]): List of documents to ingest.
            chunk_size (int): Number of documents to process in each chunk.
            resume (bool): Whether to resume from the last processed chunk.
        """
        if documents:
            # Determine the number of chunks
            total_chunks = (len(documents) + chunk_size - 1) // chunk_size
            processed_chunks_file = "processed_chunks.log"

            # Load processed chunks if resuming
            processed_chunks = set()
            if resume and os.path.exists(processed_chunks_file):
                with open(processed_chunks_file, "r") as f:
                    processed_chunks = set(map(int, f.read().splitlines()))
            
            # Process documents in chunks
            for chunk_index in range(total_chunks):
                if chunk_index in processed_chunks:
                    logging.info(f"Skipping already processed chunk {chunk_index + 1}/{total_chunks}")
                    continue
                
                # Get the current chunk
                start = chunk_index * chunk_size
                end = min(start + chunk_size, len(documents))
                chunk = documents[start:end]
                logging.info(f"Processing chunk {chunk_index + 1}/{total_chunks} ({len(chunk)} documents)...")

                # Split documents
                split_docs = self.recursive_splitter.split_documents(
                    self.semantic_splitter.create_documents([doc.page_content for doc in chunk])
                )

                # Add metadata back
                for split_doc, original_doc in zip(split_docs, chunk):
                    split_doc.metadata = original_doc.metadata

                # Ingest the chunk into the vector store
                logging.info(f"Ingesting chunk {chunk_index + 1}/{total_chunks} into the vector store...")
                Qdrant.from_documents(
                    documents=split_docs,
                    embedding=self.embeddings,
                    path=Config.Path.DATABASE_DIR,
                    collection_name=Config.Database.DOCUMENTS_COLLECTION,
                    
                )

                # Mark the chunk as processed
                with open(processed_chunks_file, "a") as f:
                    f.write(f"{chunk_index}\n")
        else:
            # Load existing vector store
            logging.info("Loading existing vector store...")
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.DOCUMENTS_COLLECTION,
                path=Config.Path.DATABASE_DIR,
        )
    
    def ingest_summary(self, documents: list[Document] = None, chunk_size: int = 1000, resume: bool = True) -> None:
        """
        Ingest summary documents into a separate vector store, processing them in chunks.

        Args:
            documents (list[Document]): List of documents to ingest.
            chunk_size (int): Number of documents to process in each chunk.
            resume (bool): Whether to resume from the last processed chunk.
        """
        if documents:
            # Determine the number of chunks
            total_chunks = (len(documents) + chunk_size - 1) // chunk_size
            processed_chunks_file = "processed_summary_chunks.log"

            # Load processed chunks if resuming
            processed_chunks = set()
            if resume and os.path.exists(processed_chunks_file):
                with open(processed_chunks_file, "r") as f:
                    processed_chunks = set(map(int, f.read().splitlines()))

            # Process documents in chunks
            for chunk_index in range(total_chunks):
                if chunk_index in processed_chunks:
                    logging.info(f"Skipping already processed summary chunk {chunk_index + 1}/{total_chunks}")
                    continue

                # Get the current chunk
                start = chunk_index * chunk_size
                end = min(start + chunk_size, len(documents))
                chunk = documents[start:end]
                logging.info(f"Processing summary chunk {chunk_index + 1}/{total_chunks} ({len(chunk)} documents)...")

                # Split documents
                split_docs = self.recursive_splitter.split_documents(
                    self.semantic_splitter.create_documents([doc.page_content for doc in chunk])
                )

                # Add metadata back
                for split_doc, original_doc in zip(split_docs, chunk):
                    split_doc.metadata = original_doc.metadata

                # Ingest the chunk into the summary vector store
                logging.info(f"Ingesting summary chunk {chunk_index + 1}/{total_chunks} into the summary vector store...")
                
                Qdrant.from_documents(
                    documents=split_docs,
                    embedding=self.embeddings,
                    path=Config.Path.DATABASE_DIR,
                    collection_name=Config.Database.SUMMARY_COLLECTION,  # <- different index here
                )

                # Mark the chunk as processed
                with open(processed_chunks_file, "a") as f:
                    f.write(f"{chunk_index}\n")
        else:
            # Load existing summary vector store
            logging.info("Loading existing summary vector store...")
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.SUMMARY_COLLECTION,
                path=Config.Path.DATABASE_DIR,
            )