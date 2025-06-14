import warnings

# Handle PyTorch import issues with a try/except
try:
    # Disable PyTorch warnings about custom classes 
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
except ImportError:
    pass

from langchain_community.chat_models import ChatOllama
from langchain_community.document_compressors.flashrank_rerank import \
    FlashrankRerank
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from ragbase.config import Config


def create_llm() -> BaseLanguageModel:
    if Config.Model.USE_LOCAL:
        return ChatOllama(
            model=Config.Model.LOCAL_LLM,
            temperature=Config.Model.TEMPERATURE,
            keep_alive="1h",
            max_tokens=Config.Model.MAX_TOKENS,
        )
    else:
         return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0.4,
        max_output_tokens=Config.Model.MAX_TOKENS,
    )
        # return ChatGroq(
        #     temperature=Config.Model.TEMPERATURE,
        #     model_name=Config.Model.REMOTE_LLM,
        #     max_tokens=Config.Model.MAX_TOKENS,
        # )



def create_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=Config.Model.EMBEDDINGS)


def create_reranker() -> FlashrankRerank:
    return FlashrankRerank(model=Config.Model.RERANKER)
