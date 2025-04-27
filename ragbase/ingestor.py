# import pandas as pd
# import ast 
# from pathlib import Path
# from typing import List

# from langchain_community.document_loaders import PyPDFium2Loader
# from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
# from langchain_core.vectorstores import VectorStore
# from langchain_experimental.text_splitter import SemanticChunker
# from langchain_qdrant import Qdrant
# from langchain_text_splitters import RecursiveCharacterTextSplitter

# from ragbase.config import Config
# from langchain.schema import Document


# class Ingestor:
#     def __init__(self):
#         self.embeddings = FastEmbedEmbeddings(model_name=Config.Model.EMBEDDINGS)
#         self.semantic_splitter = SemanticChunker(
#             self.embeddings, breakpoint_threshold_type="interquartile"
#         )
#         self.recursive_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=2048,
#             chunk_overlap=128,
#             add_start_index=True,
#         )

#     def ingest(self, doc_paths: List[Path]) -> VectorStore:
#         documents = []
#         for doc_path in doc_paths:
#             loaded_documents = PyPDFium2Loader(doc_path).load()
#             document_text = "\n".join([doc.page_content for doc in loaded_documents])
#             documents.extend(
#                 self.recursive_splitter.split_documents(
#                     self.semantic_splitter.create_documents([document_text])
#                 )
#             )
#         return Qdrant.from_documents(
#             documents=documents,
#             embedding=self.embeddings,
#             path=Config.Path.DATABASE_DIR,
#             collection_name=Config.Database.DOCUMENTS_COLLECTION,
#         )


# from pathlib import Path
# from typing import List

# import pandas as pd
# from langchain_core.documents import Document
# from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
# from langchain_core.vectorstores import VectorStore
# from langchain_experimental.text_splitter import SemanticChunker
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_qdrant import Qdrant

# from ragbase.config import Config


# class Ingestor:
#     def __init__(self):
#         self.embeddings = FastEmbedEmbeddings(model_name=Config.Model.EMBEDDINGS)
#         self.semantic_splitter = SemanticChunker(
#             self.embeddings, breakpoint_threshold_type="interquartile"
#         )
#         self.recursive_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=2048,
#             chunk_overlap=128,
#             add_start_index=True,
#         )

#     def ingest(self) -> VectorStore:
#         # Read predefined Excel file
#         excel_path = Config.Path.EXCEL_FILE
#         if not excel_path.exists():
#             raise FileNotFoundError(f"Excel file not found at {excel_path}")
        
#         df = pd.read_excel(excel_path)
        
#         # Create documents from question and best_answer, with labels as metadata
#         documents = []
#         for _, row in df.iterrows():
#             content = f"Question: {row['question']}\nAnswer: {row['best_answer']}"
#             doc = Document(
#                 page_content=content,
#                 metadata={"labels": row['labels'], "source": str(excel_path)}
#             )
#             documents.append(doc)
        
#         # Split documents if necessary (optional, depending on content length)
#         split_docs = self.recursive_splitter.split_documents(
#             self.semantic_splitter.create_documents([doc.page_content for doc in documents])
#         )
        
#         # Add metadata back to split documents
#         for split_doc in split_docs:
#             split_doc.metadata = documents[0].metadata  # Apply original metadata
        
#         # Create vector store
#         return Qdrant.from_documents(
#             documents=split_docs,
#             embedding=self.embeddings,
#             path=Config.Path.DATABASE_DIR,
#             collection_name=Config.Database.DOCUMENTS_COLLECTION,
#         )


# ========================= V2 =========================== #
# ingestor.py
import ast
import logging
from pathlib import Path
from typing import List

import pandas as pd
from google import genai
from google.genai import types
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

