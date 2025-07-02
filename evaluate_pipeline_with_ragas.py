"""
Code đánh giá RAG Pipeline với RAGAS
So sánh Advanced RAG vs Baseline RAG
"""

import asyncio
import os
import re
import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from google.generativeai import configure
from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_filter import LLMChainFilter
from langchain_core.tracers.stdout import ConsoleCallbackHandler

# RAGAS imports
from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig
from datasets import Dataset
import ast

# Local imports
from ragbase.chain import create_chain
from ragbase.config import Config
from ragbase.hyde import QueryTransformationHyDE
from ragbase.ingestor import Ingestor
from ragbase.model import create_embeddings, create_reranker, create_llm
from ragbase.retriever import create_hybrid_retriever
from ragbase.utils import load_documents_from_excel, load_summary_documents_from_excel

# ========================== CẤU HÌNH GEMINI KEY =============================
API_KEY = "AIzaSyBhSDC69kLBqw21VdsYvBs74q98w4dHa7E"
os.environ["GOOGLE_API_KEY"] = API_KEY
configure(api_key=API_KEY)

# ========================== PIPELINE CONFIGURATIONS =============================

class AdvancedRAGPipeline:
    """Advanced RAG Pipeline với HyDE, Routing, Hybrid Search, Reranker"""
    
    def __init__(self):
        self.client = QdrantClient(host="localhost", port=6333, timeout=10000)
        self.chain = None
        self.hyde_transformer = QueryTransformationHyDE()
        self._build_chain()
    
    def _build_chain(self):
        """Xây dựng chain với các tính năng advanced"""
        embedding_model = create_embeddings()
        
        # Load documents
        documents = load_documents_from_excel(excel_path=Config.Path.EXCEL_FILE)
        summary_documents = load_summary_documents_from_excel(excel_path=Config.Path.SUMMARY_EXCEL_FILE)
        
        # Vector stores
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="documents",
            embedding=embedding_model
        )
        
        summary_vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="summary",
            embedding=embedding_model
        )
        
        # LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=API_KEY,
            temperature=0.4,
            max_output_tokens=Config.Model.MAX_TOKENS,
        )
        
        # Hybrid retrievers
        retriever_full = create_hybrid_retriever(llm, documents, vector_store)
        retriever_summary = create_hybrid_retriever(llm, summary_documents, summary_vector_store)
        
        # Apply reranker
        if Config.Retriever.USE_RERANKER:
            retriever_full = ContextualCompressionRetriever(
                base_compressor=create_reranker(), base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=create_reranker(), base_retriever=retriever_summary
            )
        
        # Apply chain filter
        if Config.Retriever.USE_CHAIN_FILTER:
            retriever_full = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_full
            )
            retriever_summary = ContextualCompressionRetriever(
                base_compressor=LLMChainFilter.from_llm(llm), base_retriever=retriever_summary
            )
        
        self.chain = create_chain(llm, retriever_full, retriever_summary)
    
    async def generate_answer(self, question: str, session_id: str) -> Dict[str, Any]:
        """Generate answer and retrieve context"""
        # Apply HyDE transformation
        transformed_question = self.hyde_transformer.transform_query(question)
        
        full_response = ""
        documents = []
        
        async for event in self.chain.astream_events(
            {"question": transformed_question},
            config={
                "callbacks": [],
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
        
        # Clean response
        answer = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL)
        context = [doc.page_content for doc in documents]
        
        return {
            "answer": answer,
            "contexts": context,
            "question": question
        }


class BaselineRAGPipeline:
    """Baseline RAG Pipeline - không có HyDE, routing, reranker"""
    
    def __init__(self):
        self.client = QdrantClient(host="localhost", port=6333, timeout=10000)
        self.chain = None
        self._build_chain()
    
    def _build_chain(self):
        """Xây dựng chain baseline đơn giản"""
        embedding_model = create_embeddings()
        
        # Load documents
        documents = load_documents_from_excel(excel_path=Config.Path.EXCEL_FILE)
        
        # Vector store đơn giản
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="documents",
            embedding=embedding_model
        )
        
        # LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=API_KEY,
            temperature=0.4,
            max_output_tokens=Config.Model.MAX_TOKENS,
        )
        
        # Simple retriever - chỉ similarity search, không hybrid, không reranker
        retriever_simple = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": Config.Retriever.FULL_RETRIEVAL_K}
        )
        
        # Sử dụng cùng function create_chain nhưng với retriever đơn giản
        # Do create_chain expect 2 retrievers, ta dùng cùng retriever cho cả 2
        self.chain = create_chain(llm, retriever_simple, retriever_simple)
    
    async def generate_answer(self, question: str, session_id: str) -> Dict[str, Any]:
        """Generate answer với baseline pipeline"""
        full_response = ""
        documents = []
        
        async for event in self.chain.astream_events(
            {"question": question},  # Không HyDE transformation
            config={
                "callbacks": [],
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
        
        answer = full_response
        context = [doc.page_content for doc in documents]
        
        return {
            "answer": answer,
            "contexts": context,
            "question": question
        }


class RAGASEvaluator:
    """Class đánh giá RAGAS"""
    
    def __init__(self):
        # Configure RAGAS với Gemini sử dụng LangchainLLMWrapper
        self.llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=API_KEY,
            temperature=0.0,
            max_tokens=8000,
            timeout=None,
            max_retries=3,
        ))
        
        # Embedding model
        self.embeddings = create_embeddings()
        
        # Run config
        self.run_config = RunConfig(
            timeout=120,
            max_retries=3,
            max_wait=30,
            max_workers=4
        )
        
        # Set up metrics
        self.metrics = [
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ]
    
    def evaluate_pipeline(self, dataset: Dataset) -> Dict[str, float]:
        """Đánh giá pipeline với RAGAS metrics"""
        try:
            result = evaluate(
                dataset=dataset,
                llm=self.llm,
                embeddings=self.embeddings,
                metrics=self.metrics,
                run_config=self.run_config
            )
            return result
        except Exception as e:
            print(f"❌ Lỗi khi đánh giá RAGAS: {e}")
            return {}
    
    def prepare_dataset(self, data: List[Dict]) -> Dataset:
        """Chuẩn bị dataset cho RAGAS"""
        # Xử lý dữ liệu tương tự như trong notebook
        processed_data = []
        
        for item in data:
            # Đảm bảo contexts là list
            contexts = item["contexts"]
            if isinstance(contexts, str):
                contexts = [contexts]
            elif not isinstance(contexts, list):
                contexts = [str(contexts)]
            
            processed_data.append({
                "question": str(item["question"]),
                "answer": str(item["answer"]),
                "contexts": contexts,
                "ground_truth": str(item["ground_truth"])
            })
        
        # Tạo dataset từ dict
        dataset_dict = {
            "question": [item["question"] for item in processed_data],
            "answer": [item["answer"] for item in processed_data],
            "contexts": [item["contexts"] for item in processed_data],
            "ground_truth": [item["ground_truth"] for item in processed_data]
        }
        
        return Dataset.from_dict(dataset_dict)


async def test_pipelines_on_samples(n_samples: int = 5):
    """Test và so sánh 2 pipeline trên một vài mẫu"""
    print("🚀 Đang khởi tạo pipelines...")
    
    # Load test data
    test_data = pd.read_excel("./data/generated_test_dataset_question_answers_best_answer_final.xlsx")
    sample_data = test_data.head(n_samples)
    
    # Initialize pipelines
    advanced_pipeline = AdvancedRAGPipeline()
    baseline_pipeline = BaselineRAGPipeline()
    
    print(f"📊 Testing trên {n_samples} mẫu...\n")
    
    results = []
    
    for i, row in sample_data.iterrows():
        question = row.get("question_generated", "")
        ground_truth = row.get("best_answer_generated", "")
        
        if not question:
            continue
            
        print(f"=" * 80)
        print(f"🔍 QUESTION {i+1}: {question}")
        print(f"🎯 GROUND TRUTH: {ground_truth[:200]}...")
        print()
        
        # Advanced RAG
        print("🚀 ADVANCED RAG PIPELINE:")
        try:
            advanced_result = await advanced_pipeline.generate_answer(question, f"advanced-{i}")
            print(f"📝 Answer: {advanced_result['answer'][:200]}...")
            print(f"📚 Contexts ({len(advanced_result['contexts'])}): {[ctx[:100] + '...' for ctx in advanced_result['contexts'][:2]]}")
        except Exception as e:
            print(f"❌ Lỗi Advanced RAG: {e}")
            advanced_result = {"answer": "", "contexts": [], "question": question}
        
        print()
        
        # Baseline RAG
        print("📊 BASELINE RAG PIPELINE:")
        try:
            baseline_result = await baseline_pipeline.generate_answer(question, f"baseline-{i}")
            print(f"📝 Answer: {baseline_result['answer'][:200]}...")
            print(f"📚 Contexts ({len(baseline_result['contexts'])}): {[ctx[:100] + '...' for ctx in baseline_result['contexts'][:2]]}")
        except Exception as e:
            print(f"❌ Lỗi Baseline RAG: {e}")
            baseline_result = {"answer": "", "contexts": [], "question": question}
        
        print()
        
        # Store results
        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "advanced_answer": advanced_result["answer"],
            "advanced_contexts": advanced_result["contexts"],
            "baseline_answer": baseline_result["answer"],
            "baseline_contexts": baseline_result["contexts"]
        })
        
        time.sleep(2)  # Rate limit protection
    
    return results


async def evaluate_pipelines_batch(batch_size: int = 50, max_batches: int = 5):
    """Đánh giá pipeline theo batch và tính RAGAS score"""
    print("🚀 Bắt đầu đánh giá pipeline với RAGAS...")
    
    # Load test data
    test_data = pd.read_excel("./data/generated_test_dataset_question_answers_best_answer_final.xlsx")
    
    # Initialize pipelines và evaluator
    advanced_pipeline = AdvancedRAGPipeline()
    baseline_pipeline = BaselineRAGPipeline()
    evaluator = RAGASEvaluator()
    
    # Create output directory
    output_dir = "./data/ragas_evaluation_results"
    os.makedirs(output_dir, exist_ok=True)
    
    # Split data into batches
    batches = np.array_split(test_data.head(batch_size * max_batches), max_batches)
    
    all_advanced_results = []
    all_baseline_results = []
    
    for batch_idx, batch in enumerate(batches):
        print(f"\n🔄 Processing batch {batch_idx + 1}/{len(batches)}...")
        
        advanced_batch_results = []
        baseline_batch_results = []
        
        for i, row in batch.iterrows():
            question = row.get("question_generated", "")
            ground_truth = row.get("best_answer_generated", "")
            
            if not question:
                continue
            
            print(f"Processing question {i+1}...")
            
            try:
                # Advanced pipeline
                advanced_result = await advanced_pipeline.generate_answer(question, f"adv-{batch_idx}-{i}")
                advanced_batch_results.append({
                    "question": question,
                    "answer": advanced_result["answer"],
                    "contexts": advanced_result["contexts"],
                    "ground_truth": ground_truth
                })
                
                # Baseline pipeline
                baseline_result = await baseline_pipeline.generate_answer(question, f"base-{batch_idx}-{i}")
                baseline_batch_results.append({
                    "question": question,
                    "answer": baseline_result["answer"],
                    "contexts": baseline_result["contexts"],
                    "ground_truth": ground_truth
                })
                
                time.sleep(1)  # Rate limit protection
                
            except Exception as e:
                print(f"❌ Lỗi tại question {i}: {e}")
                continue
        
        # Save batch results
        advanced_df = pd.DataFrame(advanced_batch_results)
        baseline_df = pd.DataFrame(baseline_batch_results)
        
        advanced_df.to_excel(f"{output_dir}/advanced_batch_{batch_idx+1}.xlsx", index=False)
        baseline_df.to_excel(f"{output_dir}/baseline_batch_{batch_idx+1}.xlsx", index=False)
        
        # Evaluate with RAGAS
        if advanced_batch_results and baseline_batch_results:
            print(f"📊 Evaluating batch {batch_idx + 1} with RAGAS...")
            
            # Advanced pipeline evaluation
            advanced_dataset = evaluator.prepare_dataset(advanced_batch_results)
            advanced_scores = evaluator.evaluate_pipeline(advanced_dataset)
            
            # Baseline pipeline evaluation
            baseline_dataset = evaluator.prepare_dataset(baseline_batch_results)
            baseline_scores = evaluator.evaluate_pipeline(baseline_dataset)
            
            # Print results
            print(f"\n📈 RAGAS SCORES - Batch {batch_idx + 1}:")
            print("=" * 60)
            print(f"{'Metric':<20} {'Advanced':<15} {'Baseline':<15} {'Improvement'}")
            print("-" * 60)
            
            # Convert EvaluationResult to dict if needed
            if hasattr(advanced_scores, 'to_pandas'):
                adv_dict = advanced_scores.to_pandas().to_dict()
            else:
                adv_dict = dict(advanced_scores) if hasattr(advanced_scores, '__iter__') else {}
                
            if hasattr(baseline_scores, 'to_pandas'):
                base_dict = baseline_scores.to_pandas().to_dict()
            else:
                base_dict = dict(baseline_scores) if hasattr(baseline_scores, '__iter__') else {}
            
            # Try different ways to access metrics
            for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
                # Try direct attribute access first
                try:
                    adv_score = getattr(advanced_scores, metric, 0)
                except:
                    adv_score = adv_dict.get(metric, 0)
                
                try:
                    base_score = getattr(baseline_scores, metric, 0)
                except:
                    base_score = base_dict.get(metric, 0)
                
                improvement = ((adv_score - base_score) / base_score * 100) if base_score > 0 else 0
                
                print(f"{metric:<20} {adv_score:<15.4f} {base_score:<15.4f} {improvement:+.2f}%")
            
            # Save scores
            scores_data = []
            for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
                try:
                    adv_score = getattr(advanced_scores, metric, 0)
                except:
                    adv_score = adv_dict.get(metric, 0)
                
                try:
                    base_score = getattr(baseline_scores, metric, 0)
                except:
                    base_score = base_dict.get(metric, 0)
                
                scores_data.append({
                    "pipeline": "advanced", 
                    "batch": batch_idx + 1, 
                    "metric": metric,
                    "score": adv_score
                })
                scores_data.append({
                    "pipeline": "baseline", 
                    "batch": batch_idx + 1, 
                    "metric": metric,
                    "score": base_score
                })
            
            scores_df = pd.DataFrame(scores_data)
            scores_df.to_excel(f"{output_dir}/ragas_scores_batch_{batch_idx+1}.xlsx", index=False)
        
        all_advanced_results.extend(advanced_batch_results)
        all_baseline_results.extend(baseline_batch_results)
        
        print(f"✅ Completed batch {batch_idx + 1}")
    
    # Final evaluation on all data
    if all_advanced_results and all_baseline_results:
        print("\n🎯 FINAL EVALUATION ON ALL DATA:")
        print("=" * 80)
        
        # Final RAGAS evaluation
        final_advanced_dataset = evaluator.prepare_dataset(all_advanced_results)
        final_baseline_dataset = evaluator.prepare_dataset(all_baseline_results)
        
        final_advanced_scores = evaluator.evaluate_pipeline(final_advanced_dataset)
        final_baseline_scores = evaluator.evaluate_pipeline(final_baseline_dataset)
        
        # Print final comparison
        print(f"{'Metric':<20} {'Advanced':<15} {'Baseline':<15} {'Improvement'}")
        print("-" * 70)
        
        # Convert EvaluationResult to dict if needed
        if hasattr(final_advanced_scores, 'to_pandas'):
            final_adv_dict = final_advanced_scores.to_pandas().to_dict()
        else:
            final_adv_dict = dict(final_advanced_scores) if hasattr(final_advanced_scores, '__iter__') else {}
            
        if hasattr(final_baseline_scores, 'to_pandas'):
            final_base_dict = final_baseline_scores.to_pandas().to_dict()
        else:
            final_base_dict = dict(final_baseline_scores) if hasattr(final_baseline_scores, '__iter__') else {}
        
        for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
            try:
                adv_score = getattr(final_advanced_scores, metric, 0)
            except:
                adv_score = final_adv_dict.get(metric, 0)
            
            try:
                base_score = getattr(final_baseline_scores, metric, 0)
            except:
                base_score = final_base_dict.get(metric, 0)
            
            improvement = ((adv_score - base_score) / base_score * 100) if base_score > 0 else 0
            
            print(f"{metric:<20} {adv_score:<15.4f} {base_score:<15.4f} {improvement:+.2f}%")
        
        # Save final results
        final_scores_data = []
        for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
            try:
                adv_score = getattr(final_advanced_scores, metric, 0)
            except:
                adv_score = final_adv_dict.get(metric, 0)
            
            try:
                base_score = getattr(final_baseline_scores, metric, 0)
            except:
                base_score = final_base_dict.get(metric, 0)
            
            final_scores_data.append({
                "pipeline": "advanced", 
                "batch": "final", 
                "metric": metric,
                "score": adv_score
            })
            final_scores_data.append({
                "pipeline": "baseline", 
                "batch": "final", 
                "metric": metric,
                "score": base_score
            })
        
        final_scores_df = pd.DataFrame(final_scores_data)
        final_scores_df.to_excel(f"{output_dir}/final_ragas_scores.xlsx", index=False)
        
        # Save all results
        pd.DataFrame(all_advanced_results).to_excel(f"{output_dir}/all_advanced_results.xlsx", index=False)
        pd.DataFrame(all_baseline_results).to_excel(f"{output_dir}/all_baseline_results.xlsx", index=False)
    
    print(f"\n🎉 Evaluation completed! Results saved in {output_dir}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode - chỉ test vài mẫu
        print("🧪 TEST MODE - Testing few samples...")
        results = asyncio.run(test_pipelines_on_samples(n_samples=3))
        print("\n✅ Test completed!")
        
    else:
        # Full evaluation mode
        print("🔥 FULL EVALUATION MODE")
        asyncio.run(evaluate_pipelines_batch(batch_size=50, max_batches=5))
