#!/usr/bin/env python3
"""
Script để rebuild toàn bộ vector database với format mới
Includes improved best answer matching và clean text formatting
"""

import pandas as pd
import logging
from datetime import datetime
import ast
import json
import difflib
from pathlib import Path
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

from ragbase.ingestor import Ingestor
from ragbase.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImprovedIngestor:
    """Improved ingestor với clean formatting và best answer matching"""
    
    def __init__(self):
        self.ingestor = Ingestor()
        self.client = QdrantClient(host="localhost", port=6333, prefer_grpc=False)
        
    def clean_answer_text(self, answer_text):
        """Clean answer text bỏ brackets và format lại"""
        answer_text = str(answer_text).strip()
        
        # Remove list brackets if present
        if answer_text.startswith("['") and answer_text.endswith("']"):
            answer_text = answer_text[2:-2]
        elif answer_text.startswith('[') and answer_text.endswith(']'):
            try:
                parsed = ast.literal_eval(answer_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    answer_text = str(parsed[0])
            except:
                answer_text = answer_text[1:-1]
        
        return answer_text.strip()
    
    def find_best_answer_match(self, best_answer, answers, threshold=0.8):
        """Tìm best answer trong danh sách answers với similarity matching"""
        if not best_answer or not answers:
            return -1, 0.0
        
        best_answer = self.clean_answer_text(best_answer)
        max_ratio = 0.0
        best_index = -1
        
        for i, answer in enumerate(answers):
            answer = self.clean_answer_text(answer)
            
            # Exact match first
            if answer == best_answer:
                return i, 1.0
            
            # Similarity matching
            ratio = difflib.SequenceMatcher(None, best_answer, answer).ratio()
            if ratio > max_ratio:
                max_ratio = ratio
                best_index = i
        
        if max_ratio >= threshold:
            return best_index, max_ratio
        
        return -1, max_ratio
    
    def create_regular_document(self, row, doc_id):
        """Tạo document cho regular collection với format mới"""
        try:
            # Extract data
            question = str(row.get('question', ''))
            labels = str(row.get('labels', ''))
            best_answer = str(row.get('best_answer', ''))
            
            # Parse answers
            answers = []
            if 'answers' in row and pd.notna(row['answers']):
                answers_raw = str(row['answers'])
                try:
                    if answers_raw.startswith('[') and answers_raw.endswith(']'):
                        answers = ast.literal_eval(answers_raw)
                    else:
                        answers = [answers_raw]
                except:
                    answers = [answers_raw]
            else:
                # Get from individual answer columns
                for col in ['answer1', 'answer2', 'answer3', 'answer4', 'answer5']:
                    if col in row and pd.notna(row.get(col)):
                        answer_text = str(row.get(col))
                        if answer_text.strip():
                            answers.append(answer_text.strip())
            
            if not answers:
                logger.warning(f"No answers found for row {doc_id}")
                return None
            
            # Find best answer match
            best_index, similarity = self.find_best_answer_match(best_answer, answers)
            
            # If no good match found, add best answer to list
            if best_index < 0 and best_answer:
                answers.append(best_answer)
                best_index = len(answers) - 1
                similarity = 1.0
            
            # Create formatted answers với clean text
            formatted_answers = []
            for j, answer in enumerate(answers):
                clean_answer = self.clean_answer_text(answer)
                if clean_answer:
                    if j == best_index:
                        formatted_answers.append(f"⭐ BEST: {clean_answer}")
                    else:
                        formatted_answers.append(clean_answer)
            
            # Create content
            if formatted_answers:
                answers_text = "\n\n".join(formatted_answers)
            else:
                answers_text = "No answers available"
            
            content = f"Question: {question}\n\nAnswers:\n{answers_text}"
            
            # Create document with metadata
            doc = Document(
                page_content=content,
                metadata={
                    "question": question,
                    "labels": labels,
                    "best_answer": best_answer,
                    "num_answers": len(answers),
                    "doc_id": doc_id,
                    "source": "mental_health_data_official.xlsx",
                    "timestamp": datetime.now().isoformat(),
                    "has_best_marking": best_index >= 0,
                    "best_match_similarity": similarity,
                    "best_answer_index": best_index,
                    "collection_type": "regular"
                }
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"Error creating document for row {doc_id}: {e}")
            return None
    
    def create_summary_document(self, row, doc_id):
        """Tạo document cho summary collection"""
        try:
            question = str(row.get('question', ''))
            summary = str(row.get('summary', ''))
            labels = str(row.get('labels', ''))
            
            if not summary or summary == 'nan':
                logger.warning(f"No summary found for row {doc_id}")
                return None
            
            # Create content
            content = f"Question: {question}\n\nSummary: {summary}"
            
            # Create document
            doc = Document(
                page_content=content,
                metadata={
                    "question": question,
                    "labels": labels,
                    "summary": summary,
                    "doc_id": doc_id,
                    "source": "summary_mental_health_data_official.xlsx",
                    "timestamp": datetime.now().isoformat(),
                    "collection_type": "summary"
                }
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"Error creating summary document for row {doc_id}: {e}")
            return None
    
    def recreate_collections(self):
        """Recreate collections from scratch"""
        logger.info("Recreating collections...")
        
        # Delete existing collections
        try:
            self.client.delete_collection("documents")
            logger.info("Deleted existing 'documents' collection")
        except:
            logger.info("'documents' collection doesn't exist or already deleted")
        
        try:
            self.client.delete_collection("summary")
            logger.info("Deleted existing 'summary' collection")
        except:
            logger.info("'summary' collection doesn't exist or already deleted")
        
        # Create new collections
        vector_size = 1024  # multilingual-e5-large-instruct vector size
        
        self.client.create_collection(
            collection_name="documents",
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        logger.info("Created new 'documents' collection")
        
        self.client.create_collection(
            collection_name="summary",
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        logger.info("Created new 'summary' collection")
    
    def ingest_regular_documents(self, excel_path, batch_size=100):
        """Ingest regular documents"""
        logger.info(f"📄 Loading regular data from {excel_path}")
        df = pd.read_excel(excel_path)
        logger.info(f"📊 Loaded {len(df)} regular records")
        
        documents = []
        failed_count = 0
        processed_count = 0
        
        logger.info(f"🔄 Starting processing with batch size {batch_size}...")
        
        for i, row in df.iterrows():
            # Log progress every 1000 records
            if i > 0 and i % 1000 == 0:
                progress = (i / len(df)) * 100
                logger.info(f"📈 Progress: {i}/{len(df)} ({progress:.1f}%) - Success: {processed_count}, Failed: {failed_count}")
            
            doc = self.create_regular_document(row, i)
            if doc:
                documents.append(doc)
                processed_count += 1
                
                # Log first few documents for debugging
                if i < 3:
                    logger.info(f"✅ Document {i+1} created:")
                    logger.info(f"   📝 Content length: {len(doc.page_content)} chars")
                    logger.info(f"   📊 Metadata: {doc.metadata.get('num_answers')} answers, best_index: {doc.metadata.get('best_answer_index')}")
                    logger.info(f"   🏷️  Labels: {doc.metadata.get('labels')}")
            else:
                failed_count += 1
                if i < 10:  # Log first few failures
                    logger.warning(f"❌ Failed to create document for row {i+1}")
            
            # Process in batches
            if len(documents) >= batch_size:
                logger.info(f"🚀 Ingesting batch: {len(documents)} documents (rows {i-len(documents)+2}-{i+1})")
                self._ingest_batch(documents, "documents")
                logger.info(f"✅ Batch completed. Total processed: {i+1}/{len(df)}")
                documents = []
        
        # Process remaining documents
        if documents:
            logger.info(f"🚀 Ingesting final batch: {len(documents)} documents")
            self._ingest_batch(documents, "documents")
        
        logger.info(f"✅ Regular documents ingestion completed!")
        logger.info(f"📊 Results: Success: {processed_count}, Failed: {failed_count}, Total: {len(df)}")
        
        # Get final count
        collection_info = self.client.get_collection("documents")
        logger.info(f"🎯 Final 'documents' collection size: {collection_info.points_count} points")
    
    def ingest_summary_documents(self, excel_path, batch_size=100):
        """Ingest summary documents"""
        logger.info(f"📋 Loading summary data from {excel_path}")
        
        try:
            df = pd.read_excel(excel_path)
            logger.info(f"📊 Loaded {len(df)} summary records")
        except FileNotFoundError:
            logger.warning(f"❌ Summary file {excel_path} not found, skipping summary ingestion")
            return
        
        documents = []
        failed_count = 0
        processed_count = 0
        
        logger.info(f"🔄 Starting summary processing with batch size {batch_size}...")
        
        for i, row in df.iterrows():
            # Log progress every 1000 records
            if i > 0 and i % 1000 == 0:
                progress = (i / len(df)) * 100
                logger.info(f"📈 Summary Progress: {i}/{len(df)} ({progress:.1f}%) - Success: {processed_count}, Failed: {failed_count}")
            
            doc = self.create_summary_document(row, i)
            if doc:
                documents.append(doc)
                processed_count += 1
                
                # Log first few documents for debugging
                if i < 3:
                    logger.info(f"✅ Summary document {i+1} created:")
                    logger.info(f"   📝 Content length: {len(doc.page_content)} chars")
                    logger.info(f"   🏷️  Labels: {doc.metadata.get('labels')}")
            else:
                failed_count += 1
                if i < 10:  # Log first few failures
                    logger.warning(f"❌ Failed to create summary document for row {i+1}")
            
            # Process in batches
            if len(documents) >= batch_size:
                logger.info(f"🚀 Ingesting summary batch: {len(documents)} documents (rows {i-len(documents)+2}-{i+1})")
                self._ingest_batch(documents, "summary")
                logger.info(f"✅ Summary batch completed. Total processed: {i+1}/{len(df)}")
                documents = []
        
        # Process remaining documents
        if documents:
            logger.info(f"🚀 Ingesting final summary batch: {len(documents)} documents")
            self._ingest_batch(documents, "summary")
        
        logger.info(f"✅ Summary documents ingestion completed!")
        logger.info(f"📊 Summary Results: Success: {processed_count}, Failed: {failed_count}, Total: {len(df)}")
        
        # Get final count
        collection_info = self.client.get_collection("summary")
        logger.info(f"🎯 Final 'summary' collection size: {collection_info.points_count} points")
    
    def _ingest_batch(self, documents, collection_name):
        """Ingest a batch of documents"""
        if not documents:
            return
        
        batch_start_time = datetime.now()
        logger.info(f"🔄 Processing batch for '{collection_name}': {len(documents)} documents")
        
        try:
            # Apply smart splitting
            logger.info(f"✂️  Applying smart splitting...")
            final_documents = []
            for doc in documents:
                split_docs = self.ingestor._smart_split_document(doc)
                final_documents.extend(split_docs)
            
            logger.info(f"📄 After splitting: {len(documents)} → {len(final_documents)} documents")
            
            # Create embeddings and points
            logger.info(f"🧠 Creating embeddings for {len(final_documents)} documents...")
            points = []
            
            for i, doc in enumerate(final_documents):
                if i > 0 and i % 50 == 0:  # Log every 50 embeddings
                    logger.info(f"   📊 Embedded {i}/{len(final_documents)} documents...")
                
                # Create embedding
                embedding = self.ingestor.embeddings.embed_query(doc.page_content)
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "page_content": doc.page_content,
                        **doc.metadata
                    }
                )
                points.append(point)
            
            # Upsert to Qdrant
            logger.info(f"💾 Upserting {len(points)} points to Qdrant '{collection_name}'...")
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            batch_time = (datetime.now() - batch_start_time).total_seconds()
            logger.info(f"✅ Batch completed in {batch_time:.2f}s - {len(points)} points added to '{collection_name}'")
            
        except Exception as e:
            logger.error(f"❌ Error ingesting batch to {collection_name}: {e}")
            raise

def main():
    """Main rebuild function"""
    start_time = datetime.now()
    logger.info("🚀 Starting complete database rebuild with new format")
    logger.info(f"⏰ Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize ingestor
    logger.info("🔧 Initializing improved ingestor...")
    ingestor = ImprovedIngestor()
    
    # Recreate collections
    logger.info("🗑️  Recreating collections...")
    ingestor.recreate_collections()
    
    # Define file paths
    regular_excel = Path("data/mental_health_data_official.xlsx")
    summary_excel = Path("data/summary_mental_health_data_official.xlsx")
    
    logger.info(f"📁 File paths:")
    logger.info(f"   Regular: {regular_excel} ({'✅ exists' if regular_excel.exists() else '❌ missing'})")
    logger.info(f"   Summary: {summary_excel} ({'✅ exists' if summary_excel.exists() else '❌ missing'})")
    
    # Ingest regular documents
    if regular_excel.exists():
        logger.info("📄 ========== STARTING REGULAR DOCUMENTS INGESTION ==========")
        ingestor.ingest_regular_documents(regular_excel)
        logger.info("📄 ========== REGULAR DOCUMENTS COMPLETED ==========")
    else:
        logger.error(f"❌ Regular excel file not found: {regular_excel}")
        return
    
    # Ingest summary documents
    if summary_excel.exists():
        logger.info("📋 ========== STARTING SUMMARY DOCUMENTS INGESTION ==========")
        ingestor.ingest_summary_documents(summary_excel)
        logger.info("📋 ========== SUMMARY DOCUMENTS COMPLETED ==========")
    else:
        logger.warning(f"⚠️  Summary excel file not found: {summary_excel}")
    
    # Final statistics
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    logger.info("🎉 ========== DATABASE REBUILD COMPLETED! ==========")
    logger.info(f"⏰ End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
    
    try:
        docs_info = ingestor.client.get_collection("documents")
        summary_info = ingestor.client.get_collection("summary")
        
        logger.info("📊 ========== FINAL STATISTICS ==========")
        logger.info(f"   🏗️  Documents collection: {docs_info.points_count:,} points")
        logger.info(f"   📋 Summary collection: {summary_info.points_count:,} points")
        logger.info(f"   🎯 Total points: {docs_info.points_count + summary_info.points_count:,}")
        logger.info(f"   🧠 Vector size: {docs_info.config.params.vectors.size}")
        logger.info(f"   ⚡ Average speed: {(docs_info.points_count + summary_info.points_count)/total_time:.1f} points/second")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Error getting final statistics: {e}")

if __name__ == "__main__":
    main()
