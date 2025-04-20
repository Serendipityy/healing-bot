# preprocess.py
import pandas as pd
from langchain_core.documents import Document
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import Qdrant
from ragbase.config import Config
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def preprocess_excel():
    # Initialize embeddings and splitters
    embeddings = FastEmbedEmbeddings(model_name=Config.Model.EMBEDDINGS)
    semantic_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="interquartile")
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2048,
        chunk_overlap=128,
        add_start_index=True,
    )

    # Read Excel file
    excel_path = Config.Path.EXCEL_FILE
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found at {excel_path}")
    
    logging.info(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    
    # Create documents in batches
    documents = []
    batch_size = 1000  # Process 1000 rows at a time
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        for _, row in batch.iterrows():
            content = f"Question: {row['question']}\nAnswer: {row['best_answer']}"
            doc = Document(
                page_content=content,
                metadata={"labels": row['labels'], "source": str(excel_path)}
            )
            documents.append(doc)
        logging.info(f"Processed {len(documents)} documents")
    
    # Split documents
    logging.info("Splitting documents...")
    split_docs = recursive_splitter.split_documents(
        semantic_splitter.create_documents([doc.page_content for doc in documents])
    )
    
    # Add metadata back to split documents
    for split_doc in split_docs:
        split_doc.metadata = documents[0].metadata  # Apply original metadata
    
    # Create and save vector store
    logging.info("Creating vector store...")
    vector_store = Qdrant.from_documents(
        documents=split_docs,
        embedding=embeddings,
        path=Config.Path.DATABASE_DIR,
        collection_name=Config.Database.DOCUMENTS_COLLECTION,
    )
    logging.info(f"Vector store created and saved at {Config.Path.DATABASE_DIR}")

if __name__ == "__main__":
    preprocess_excel()