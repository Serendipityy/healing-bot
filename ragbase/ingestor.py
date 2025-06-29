"""
Simple and effective ingestor without over-splitting
"""
import ast
import logging
import os
from pathlib import Path
from typing import List

import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_qdrant import Qdrant
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ragbase.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Ingestor:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.Model.EMBEDDINGS)
        # Sử dụng chỉ một splitter với cấu hình tối ưu cho Q&A
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,  # Đủ lớn để giữ nguyên context của Q&A
            chunk_overlap=200,  # Overlap nhỏ để tránh trùng lặp
            add_start_index=True,
            separators=["\n\nQuestion:", "\n\nBest answer:", "\n\nAnswers:", "\n\n", "\n", " ", ""]
        )

    def _smart_split_document(self, doc: Document) -> List[Document]:
        """
        Split document thông minh - ưu tiên giữ nguyên Q&A context
        """
        content_length = len(doc.page_content)
        
        # Với nội dung nhỏ hơn 2500 chars, giữ nguyên không split
        if content_length <= 2500:
            logging.debug(f"Keeping document as-is: {content_length} chars")
            return [doc]
        
        # Với nội dung lớn hơn, split cẩn thận
        try:
            splits = self.splitter.split_documents([doc])
            if not splits:
                logging.warning("Splitter returned empty, keeping original")
                return [doc]
            
            # Preserve metadata for all splits
            for split_doc in splits:
                split_doc.metadata = doc.metadata.copy()
            
            logging.debug(f"Split document into {len(splits)} parts")
            return splits
            
        except Exception as e:
            logging.warning(f"Splitting failed: {e}, keeping original")
            return [doc]

    def ingest(self, documents: list[Document] = None, chunk_size: int = 1000, resume: bool = True) -> VectorStore:
        """
        Ingest documents với logic đơn giản và hiệu quả
        """
        if documents:
            logging.info(f"Starting ingestion of {len(documents)} documents")
            
            # Statistics before processing
            total_chars = sum(len(doc.page_content) for doc in documents)
            avg_chars = total_chars / len(documents)
            logging.info(f"Average document length: {avg_chars:.1f} characters")
            
            # Determine the number of chunks
            total_chunks = (len(documents) + chunk_size - 1) // chunk_size
            processed_chunks_file = "processed_chunks_simple.log"

            # Load processed chunks if resuming
            processed_chunks = set()
            if resume and os.path.exists(processed_chunks_file):
                with open(processed_chunks_file, "r") as f:
                    processed_chunks = set(map(int, f.read().splitlines()))
                logging.info(f"Resuming from {len(processed_chunks)} already processed chunks")
            
            # Process documents in chunks
            total_splits = 0
            for chunk_index in range(total_chunks):
                if chunk_index in processed_chunks:
                    logging.info(f"Skipping already processed chunk {chunk_index + 1}/{total_chunks}")
                    continue
                
                # Get the current chunk
                start = chunk_index * chunk_size
                end = min(start + chunk_size, len(documents))
                chunk = documents[start:end]
                logging.info(f"Processing chunk {chunk_index + 1}/{total_chunks} ({len(chunk)} documents)...")
                
                # Process each document in the chunk
                all_split_docs = []
                kept_original = 0
                split_count = 0
                
                for i, doc in enumerate(chunk):
                    try:
                        split_docs = self._smart_split_document(doc)
                        all_split_docs.extend(split_docs)
                        
                        if len(split_docs) == 1:
                            kept_original += 1
                        else:
                            split_count += len(split_docs)
                            
                    except Exception as e:
                        logging.error(f"Failed to process document {i}: {e}")
                        all_split_docs.append(doc)  # Fallback
                        kept_original += 1

                total_splits += len(all_split_docs)
                logging.info(f"Chunk {chunk_index + 1}: Kept {kept_original} original, created {split_count} new splits")
                
                # Ingest the chunk into the vector store
                logging.info(f"Ingesting chunk {chunk_index + 1}/{total_chunks} ({len(all_split_docs)} total docs) into vector store...")
                try:
                    Qdrant.from_documents(
                        documents=all_split_docs,
                        embedding=self.embeddings,
                        path=Config.Path.DATABASE_DIR,
                        collection_name=Config.Database.DOCUMENTS_COLLECTION,
                    )
                    
                    # Mark the chunk as processed
                    with open(processed_chunks_file, "a") as f:
                        f.write(f"{chunk_index}\n")
                    
                    logging.info(f"Successfully ingested chunk {chunk_index + 1}/{total_chunks}")
                    
                except Exception as e:
                    logging.error(f"Failed to ingest chunk {chunk_index + 1}: {e}")
                    raise

            logging.info(f"Ingestion completed! {len(documents)} original docs -> {total_splits} final chunks")
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.DOCUMENTS_COLLECTION,
                path=Config.Path.DATABASE_DIR,
            )
        else:
            # Load existing vector store
            logging.info("Loading existing vector store...")
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.DOCUMENTS_COLLECTION,
                path=Config.Path.DATABASE_DIR,
            )

    def ingest_summary(self, documents: list[Document] = None, chunk_size: int = 1000, resume: bool = True) -> VectorStore:
        """
        Ingest summary documents - thường ngắn hơn nên ít cần split
        """
        if documents:
            logging.info(f"Starting summary ingestion of {len(documents)} documents")
            
            # Statistics
            total_chars = sum(len(doc.page_content) for doc in documents)
            avg_chars = total_chars / len(documents)
            logging.info(f"Average summary length: {avg_chars:.1f} characters")
            
            # Determine the number of chunks
            total_chunks = (len(documents) + chunk_size - 1) // chunk_size
            processed_chunks_file = "processed_summary_chunks_simple.log"

            # Load processed chunks if resuming
            processed_chunks = set()
            if resume and os.path.exists(processed_chunks_file):
                with open(processed_chunks_file, "r") as f:
                    processed_chunks = set(map(int, f.read().splitlines()))
                logging.info(f"Resuming summary ingestion from {len(processed_chunks)} already processed chunks")

            # Process documents in chunks
            total_splits = 0
            for chunk_index in range(total_chunks):
                if chunk_index in processed_chunks:
                    logging.info(f"Skipping already processed summary chunk {chunk_index + 1}/{total_chunks}")
                    continue

                # Get the current chunk
                start = chunk_index * chunk_size
                end = min(start + chunk_size, len(documents))
                chunk = documents[start:end]
                logging.info(f"Processing summary chunk {chunk_index + 1}/{total_chunks} ({len(chunk)} documents)...")

                # For summary, usually keep original since they're already summaries
                all_split_docs = []
                for i, doc in enumerate(chunk):
                    try:
                        # Most summaries should be kept as-is
                        if len(doc.page_content) <= 3000:
                            all_split_docs.append(doc)
                        else:
                            # Only split if really necessary
                            split_docs = self._smart_split_document(doc)
                            all_split_docs.extend(split_docs)
                            
                    except Exception as e:
                        logging.error(f"Failed to process summary document {i}: {e}")
                        all_split_docs.append(doc)

                total_splits += len(all_split_docs)

                # Ingest the chunk into the summary vector store
                logging.info(f"Ingesting summary chunk {chunk_index + 1}/{total_chunks} ({len(all_split_docs)} docs)...")
                try:
                    Qdrant.from_documents(
                        documents=all_split_docs,
                        embedding=self.embeddings,
                        path=Config.Path.DATABASE_DIR,
                        collection_name=Config.Database.SUMMARY_COLLECTION,
                    )

                    # Mark the chunk as processed
                    with open(processed_chunks_file, "a") as f:
                        f.write(f"{chunk_index}\n")
                        
                    logging.info(f"Successfully ingested summary chunk {chunk_index + 1}/{total_chunks}")
                    
                except Exception as e:
                    logging.error(f"Failed to ingest summary chunk {chunk_index + 1}: {e}")
                    raise

            logging.info(f"Summary ingestion completed! {len(documents)} original docs -> {total_splits} final chunks")
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.SUMMARY_COLLECTION,
                path=Config.Path.DATABASE_DIR,
            )
        else:
            # Load existing summary vector store
            logging.info("Loading existing summary vector store...")
            return Qdrant.from_existing_collection(
                embedding=self.embeddings,
                collection_name=Config.Database.SUMMARY_COLLECTION,
                path=Config.Path.DATABASE_DIR,
            )
