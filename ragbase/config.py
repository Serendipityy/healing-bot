import os
from pathlib import Path


class Config:
    class Path:
        APP_HOME = Path(os.getenv("APP_HOME", Path(__file__).parent.parent))
        DATABASE_DIR = APP_HOME / "docs-db"
        DOCUMENTS_DIR = APP_HOME / "tmp"
        IMAGES_DIR = APP_HOME / "images"
        EXCEL_FILE = APP_HOME / "data" / "mental_health_data_official.xlsx"
        SUMMARY_EXCEL_FILE = APP_HOME / "data" / "summary_mental_health_data_official.xlsx"  
        MINI_EXCEL_FILE = APP_HOME / "data" / "mental_health_data_official_mini.xlsx"  

    class Database:
        DOCUMENTS_COLLECTION = "documents"
        SUMMARY_COLLECTION = "summary"

    class Model:
        EMBEDDINGS = "intfloat/multilingual-e5-large-instruct"
        RERANKER = "ms-marco-TinyBERT-L-2-v2"  # Nhanh nhất và chính xác nhất cho tiếng Việt
        LOCAL_LLM = "qwen2.5:latest"
        REMOTE_LLM = "deepseek-r1-distill-llama-70b"
        TEMPERATURE = 0.0
        MAX_TOKENS = 8000
        USE_LOCAL = False

    class Retriever:
        USE_RERANKER = True  # Enable for better quality, False for max speed
        USE_CHAIN_FILTER = False
        # Optimize retrieval counts for faster performance
        FULL_RETRIEVAL_K = 5  # Reduced from default 5
        SUMMARY_RETRIEVAL_K = 3  # Reduced for summary queries

    DEBUG = False
    CONVERSATION_MESSAGES_LIMIT = 10

