
from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.utils import load_summary_documents_from_excel

documents = load_summary_documents_from_excel(excel_path=Config.Path.SUMMARY_EXCEL_FILE)
summary_vector_store = Ingestor().ingest_summary(documents=documents, chunk_size=500, resume=True)
