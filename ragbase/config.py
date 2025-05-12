import os
from pathlib import Path


class Config:
    class Path:
        APP_HOME = Path(os.getenv("APP_HOME", Path(__file__).parent.parent))
        DATABASE_DIR = APP_HOME / "docs-db"
        DOCUMENTS_DIR = APP_HOME / "tmp"
        IMAGES_DIR = APP_HOME / "images"
        EXCEL_FILE = APP_HOME / "data" / "mental_health_data_official.xlsx"  
        MINI_EXCEL_FILE = APP_HOME / "data" / "mental_health_data_official_mini.xlsx"  

    class Database:
        DOCUMENTS_COLLECTION = "documents"

    class Model:
        EMBEDDINGS = "intfloat/multilingual-e5-base"
        # EMBEDDINGS = "keepitreal/vietnamese-sbert"
        RERANKER = "ms-marco-MiniLM-L-12-v2"
        LOCAL_LLM = "qwen2.5:latest"
        REMOTE_LLM = "deepseek-r1-distill-llama-70b"
        TEMPERATURE = 0.0
        MAX_TOKENS = 8000
        USE_LOCAL = False

    class Retriever:
        USE_RERANKER = True
        USE_CHAIN_FILTER = False

    DEBUG = False
    CONVERSATION_MESSAGES_LIMIT = 10

