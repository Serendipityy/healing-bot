from typing import Optional

from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.document_compressors.chain_filter import \
    LLMChainFilter
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore, VectorStoreRetriever
from langchain_qdrant import Qdrant

from ragbase.config import Config
from ragbase.model import create_embeddings, create_reranker


def create_semantic_retriever(
    llm: BaseLanguageModel, vector_store: Optional[VectorStore] = None
) -> VectorStoreRetriever:
    if not vector_store:
        vector_store = Qdrant.from_existing_collection(
            embedding=create_embeddings(),
            collection_name=Config.Database.DOCUMENTS_COLLECTION,
            path=Config.Path.DATABASE_DIR,
        )

    retriever = vector_store.as_retriever(
        search_type="similarity", search_kwargs={"k": 5}
    )

    return retriever

def create_keyword_retriever(documents: list[Document]) -> BM25Retriever:
    retriever = BM25Retriever.from_documents(documents)
    retriever.k = 5 
    return retriever

def create_hybrid_retriever(
    llm: BaseLanguageModel,
    documents: list[Document],
    vector_store: VectorStore,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> EnsembleRetriever:

    semantic_retriever = create_semantic_retriever(llm, vector_store)
    keyword_retriever = create_keyword_retriever(documents)
    # EnsembleRetriever based on Reciprocal Rank Fusion (RRF) algorithm
    hybrid_retriever = EnsembleRetriever(
        retrievers=[semantic_retriever, keyword_retriever],
        weights=[semantic_weight, keyword_weight],
    )
    return hybrid_retriever