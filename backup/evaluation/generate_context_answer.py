import asyncio
import os
import re
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import \
    LLMChainFilter
from langchain_core.tracers.stdout import ConsoleCallbackHandler

from ragbase.chain import create_chain
from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.model import create_llm, create_reranker
from ragbase.retriever import create_hybrid_retriever
from ragbase.utils import load_documents_from_excel

load_dotenv()

def build_qa_chain():
    """Khởi tạo chuỗi QA với mô hình và bộ truy xuất."""
    # Load prebuilt vector store
    documents = load_documents_from_excel(excel_path=Config.Path.EXCEL_FILE)
    vector_store = Ingestor().ingest()  # No excel_path, loads existing vector store
    
    llm = create_llm()
    # Apply Hybrid Retriever
    retriever = create_hybrid_retriever(llm, documents, vector_store)
    
    # Apply reranker (Contextual Compression Retriever)
    if Config.Retriever.USE_RERANKER:
        retriever = ContextualCompressionRetriever(
            base_compressor=create_reranker(), base_retriever=retriever
        )

    if Config.Retriever.USE_CHAIN_FILTER:
        retriever = ContextualCompressionRetriever(
            base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever
        )

    return create_chain(llm, retriever)

async def ask_question(chain, question: str, session_id: str):
    """Nhận câu hỏi và trả về câu trả lời cùng ngữ cảnh."""
    full_response = ""
    documents = []
    
    # Gọi chain và xử lý các sự kiện bất đồng bộ
    async for event in chain.astream_events(
        {"question": question},
        config={
            "callbacks": [ConsoleCallbackHandler()] if Config.DEBUG else [],
            "configurable": {"session_id": session_id},
        },
        version="v2",
        include_names=["context_retriever", "chain_answer"],
    ):
        event_type = event["event"]
        if event_type == "on_chain_stream":  # Lấy nội dung trả lời
            full_response += event["data"]["chunk"].content
        elif event_type == "on_retriever_end":  # Lấy tài liệu từ retriever
            documents.extend(event["data"]["output"])
    
    # Trích xuất nội dung từ các tài liệu
    context = [doc.page_content for doc in documents]
    
    return full_response, context

def clean_response(raw_response):
    """Loại bỏ các thẻ không cần thiết khỏi phản hồi."""
    return re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL)


def generate_answers_by_chunks(test_dataset_path, output_dir):
    """Sinh câu trả lời từ tập test theo từng chunk và lưu kết quả từng phần."""
    chunk_size=50
    # Load toàn bộ tập dữ liệu
    test_data = pd.read_excel(test_dataset_path)

    # Tách thành các chunk
    chunks = np.array_split(test_data, len(test_data) // chunk_size + 1)

    # Khởi tạo QA chain một lần
    chain = build_qa_chain()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Duyệt qua từng chunk
    for chunk_index in range(100, 120):
        print(f"🟩 Processing chunk {chunk_index + 1}/{len(chunks)}...")

        chunk = chunks[chunk_index]
        results = []
        for i, row in chunk.iterrows():
            question = row.get("question", "")
            if not question:
                continue

            print("-------------------------------------")
            print(f"Processing question {i + 1 + chunk_index * chunk_size}: {question}")

            try:
                # Gọi mô hình để tạo câu trả lời
                raw_content, context = loop.run_until_complete(
                    ask_question(chain, question, session_id=f"session-{chunk_index}-{i}")
                )

                answer = clean_response(raw_content)

                results.append({
                    "question": question,
                    "answer": answer,

                    "context": "\n".join(context) if context else "No context available"
                })

                time.sleep(10)

            except Exception as e:
                print(f"❌ Error at question {i}: {e}")
                continue

        # Lưu kết quả sau mỗi chunk
        chunk_output_path = os.path.join(output_dir, f"chunk_output_{chunk_index + 1}.xlsx")
        pd.DataFrame(results).to_excel(chunk_output_path, index=False)
        print(f"✅ Saved chunk {chunk_index + 1} to {chunk_output_path}")

    loop.close()
    print("🎉 All chunks processed.")

# Ví dụ chạy:
if __name__ == "__main__":
    test_dataset_path = "./data/generated_test_dataset_question_answers_best_answer.xlsx"
    output_dir = "./data/test_data"
    os.makedirs(output_dir, exist_ok=True)

    generate_answers_by_chunks(test_dataset_path, output_dir)
