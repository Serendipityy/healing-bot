import asyncio
import os
import re
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.generativeai import configure
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import \
    LLMChainFilter
from langchain_core.tracers.stdout import ConsoleCallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from ragbase.chain import create_chain
from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.model import create_embeddings, create_reranker
from ragbase.retriever import create_hybrid_retriever
from ragbase.utils import (load_documents_from_excel,
                           load_summary_documents_from_excel)

# ========================== CẤU HÌNH GEMINI KEY =============================

list_keys = [
    "AIzaSyBSLdACUAR5srrD_yoolWKtIZlIk5JtMSo",
    "AIzaSyB17vRD3BlCe0gzOCbvbrgwwC7zVTXlbZo",
    "AIzaSyCVA6ctW4cXNUzwUqYkR6pWbBSdh19zwvA",
    "AIzaSyCNLh5HhlIUovo8_de1RWg1jAx2Iq4Yo8g",
    "AIzaSyD_d2NNsNxVhWLK_d2yjnEQuyTNUECi1Ns",
    "AIzaSyCw371rlLG4FqlRan4C0rD280sqVga-zE4",
    "AIzaSyBctBtlbRv4aJ5cvJRZNK_sfPiBY8-6KoY",
    "AIzaSyAMKQvJs5hAup1JUNl3G29dt24m5mRLgiE",
    "AIzaSyDaVCYIC-j6BoBe4VEWPRMWnR7hTu9puZo",
    "AIzaSyBfmOEpr9mdfyEimLW1wQh9Ik4drMAdyF8",
    "AIzaSyCZ6lZNrFesfPtSkixvmaH7b8TX-UMUVBg",
    "AIzaSyDVjszXsue2Qs7rQf4-VNHhUt-1KZtQdx4",
]
current_key_index = 0

def set_gemini_key(index):
    """Cấu hình lại Gemini API key."""
    key = list_keys[index]
    os.environ["GOOGLE_API_KEY"] = key
    configure(api_key=key)
    print(f"🔐 Đang dùng Gemini API key: {key[:10]}...")

def switch_to_next_key():
    """Chuyển sang API key tiếp theo nếu bị rate limit."""
    global current_key_index
    current_key_index += 1
    if current_key_index >= len(list_keys):
        raise RuntimeError("❌ Đã hết API key Gemini có thể sử dụng.")
    print(f"🔁 Đổi sang Gemini key thứ {current_key_index + 1}")
    set_gemini_key(current_key_index)

def create_llm_from_current_key():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=list_keys[current_key_index],
        temperature=0.4,
        max_output_tokens=Config.Model.MAX_TOKENS,
    )

# ===========================================================================

set_gemini_key(current_key_index)
client = QdrantClient(host="localhost", port=6333, timeout=10000)

def build_qa_chain():
    embedding_model = create_embeddings()

    start = time.time()
    documents = load_documents_from_excel(excel_path=Config.Path.EXCEL_FILE)
    summary_documents = load_summary_documents_from_excel(excel_path=Config.Path.SUMMARY_EXCEL_FILE)

    vector_store = QdrantVectorStore(
        client=client,
        collection_name="documents",
        embedding=embedding_model
    )

    summary_vector_store = QdrantVectorStore(
        client=client,
        collection_name="summary",
        embedding=embedding_model
    )

    end = time.time()
    print(f"Thời gian embedding: {end - start} giây")

    llm = create_llm_from_current_key()

    retriever_full = create_hybrid_retriever(llm, documents, vector_store)
    retriever_summary = create_hybrid_retriever(llm, summary_documents, summary_vector_store)

    if Config.Retriever.USE_RERANKER:
        retriever_full = ContextualCompressionRetriever(
            base_compressor=create_reranker(), base_retriever=retriever_full
        )
        retriever_summary = ContextualCompressionRetriever(
            base_compressor=create_reranker(), base_retriever=retriever_summary
        )

    if Config.Retriever.USE_CHAIN_FILTER:
        retriever_full = ContextualCompressionRetriever(
            base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_full
        )
        retriever_summary = ContextualCompressionRetriever(
            base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_summary
        )

    return create_chain(llm, retriever_full, retriever_summary)

async def ask_question(chain, question: str, session_id: str):
    full_response = ""
    documents = []

    async for event in chain.astream_events(
        {"question": question},
        config={
            "callbacks": [ConsoleCallbackHandler()] if Config.DEBUG else [],
            "configurable": {"session_id": session_id},
        },
        version="v2",
        include_names=["context_retriever_full", "context_retriever_summary", "chain_answer"],
    ):
        event_type = event["event"]
        if event_type == "on_chain_stream":
            full_response += event["data"]["chunk"].content
        elif event_type == "on_retriever_end":
            documents.extend(event["data"]["output"])

    context = [doc.page_content for doc in documents]
    return full_response, context

def clean_response(raw_response):
    return re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL)

def generate_answers_by_chunks(test_dataset_path, output_dir):
    chunk_size = 1
    test_data = pd.read_excel(test_dataset_path)
    chunks = np.array_split(test_data, len(test_data) // chunk_size + 1)

    chain = build_qa_chain()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for chunk_index in range(0, 1):
        print(f"🟩 Processing chunk {chunk_index + 1}/{len(chunks)}...")
        chunk = chunks[chunk_index]
        results = []

        for i, row in chunk.iterrows():
            question = row.get("question", "")
            if not question:
                continue

            print("-------------------------------------")
            print(f"Processing question {i + 1 + chunk_index * chunk_size}: {question}")
            max_retries = 20
            retry_count = 0
            while retry_count < max_retries:
                try:
                    raw_content, context = loop.run_until_complete(
                        ask_question(chain, question, session_id=f"session-{chunk_index}-{i}")
                    )
                    answer = clean_response(raw_content)

                    results.append({
                        "question": question,
                        "answer": answer,
                        "context": "\n".join(context) if context else "No context available"
                    })

                    time.sleep(15)
                    break  # Thành công

                except Exception as e:
                    error_message = str(e)

                    if "429" in error_message:
                        print(f"⚠️ Rate limit (429) error: {e}")
                        try:
                            switch_to_next_key()
                            chain = build_qa_chain()
                            print("🔁 Switched to next key. Retrying...")
                            time.sleep(5)
                        except RuntimeError as final_error:
                            print(f"❌ {final_error}")
                            return

                    elif "503" in error_message:
                        retry_count += 1
                        print(f"🔁 Gemini quá tải (503). Đang thử lại ({retry_count}/{max_retries})...")
                        time.sleep(5)
                        continue

                    else:
                        print(f"❌ Lỗi khác tại question {i}: {e}")
                        break

        chunk_output_path = os.path.join(output_dir, f"chunk_output_{chunk_index + 1}.xlsx")
        pd.DataFrame(results).to_excel(chunk_output_path, index=False)
        print(f"✅ Saved chunk {chunk_index + 1} to {chunk_output_path}")

    loop.close()
    print("🎉 All chunks processed.")

if __name__ == "__main__":
    test_dataset_path = "./data/missing.xlsx"
    output_dir = "./data/test_data"
    os.makedirs(output_dir, exist_ok=True)
    generate_answers_by_chunks(test_dataset_path, output_dir)
