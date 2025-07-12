"""
Full RAGAS Evaluation cho 6000 mẫu
Chia thành batch 50 mẫu, lưu kết quả vào Excel
"""

import asyncio
import os
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm
import time
import json
import logging
import traceback
from pathlib import Path

# Import pipelines và RAGAS
from evaluate_pipeline_with_ragas import AdvancedRAGPipeline, BaselineRAGPipeline
from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig
from ragbase.model import create_embeddings

def pandas_to_ragas(df):
    """Converts a Pandas DataFrame into a Ragas-compatible dataset"""
    # Đảm bảo tất cả các cột văn bản đều là chuỗi và không có NaN
    text_columns = ['question', 'ground_truth', 'answer']
    for col in text_columns:
        df[col] = df[col].fillna('').astype(str)

    # Xử lý cột 'contexts' từ string hoặc JSON thành list of strings
    def parse_context(val):
        if isinstance(val, list):
            return val
        elif isinstance(val, str):
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                try:
                    import ast
                    parsed = ast.literal_eval(val)
                    return parsed if isinstance(parsed, list) else [val]
                except Exception:
                    return [val]
            elif val:
                return [val]
        return []

    df['contexts'] = df['contexts'].apply(parse_context)

    # Chuyển DataFrame thành Hugging Face dataset
    data_dict = df[['question', 'contexts', 'answer', 'ground_truth']].to_dict('list')
    ragas_testset = Dataset.from_dict(data_dict)
    return ragas_testset

API_KEY = "AIzaSyBhSDC69kLBqw21VdsYvBs74q98w4dHa7E"

class FullRAGEvaluator:
    def __init__(self):
        self.output_dir = "./data/ragas_score"
        self.advanced_dir = os.path.join(self.output_dir, "advanced_rag")
        self.baseline_dir = os.path.join(self.output_dir, "baseline_rag")
        
        # Create directories
        os.makedirs(self.advanced_dir, exist_ok=True)
        os.makedirs(self.baseline_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Progress tracking
        self.progress_file = os.path.join(self.output_dir, "progress.json")
        self.completed_batches = self.load_progress()
        
        # RAGAS setup
        self.llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=API_KEY,
            temperature=0.0,
            max_tokens=8000,
            timeout=None,
            max_retries=3,
        ))
        
        self.embedding_model = create_embeddings()
        
        self.run_config = RunConfig(
            timeout=300,  # Tăng timeout
            max_retries=10,  # Tăng retries
            max_wait=120,
            max_workers=2  # Giảm workers để ổn định hơn
        )
        
        # Pipeline instances - sẽ khởi tạo khi cần
        self.advanced_pipeline = None
        self.baseline_pipeline = None
        
        # Error tracking
        self.error_log = []
    
    def setup_logging(self):
        """Setup logging để track progress"""
        log_file = os.path.join(self.output_dir, "evaluation.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_progress(self):
        """Load progress từ file để resume nếu bị gián đoạn"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    completed = set(progress.get('completed_batches', []))
                    self.logger.info(f"📋 Loaded progress: {len(completed)} batches completed")
                    return completed
            except Exception as e:
                self.logger.warning(f"⚠️ Không thể load progress: {e}")
        return set()
    
    def save_progress(self, batch_idx):
        """Save progress"""
        self.completed_batches.add(batch_idx)
        progress = {
            'completed_batches': list(self.completed_batches),
            'last_updated': datetime.now().isoformat(),
            'total_errors': len(self.error_log)
        }
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Không thể save progress: {e}")
    
    def log_error(self, batch_idx, error_type, error_msg):
        """Log errors để debug"""
        error_info = {
            'batch': batch_idx,
            'type': error_type,
            'message': str(error_msg),
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }
        self.error_log.append(error_info)
        
        # Save error log
        error_file = os.path.join(self.output_dir, "errors.json")
        try:
            with open(error_file, 'w') as f:
                json.dump(self.error_log, f, indent=2)
        except:
            pass
    
    def initialize_pipelines(self):
        """Khởi tạo pipelines với error handling"""
        try:
            if self.advanced_pipeline is None:
                self.logger.info("🚀 Khởi tạo Advanced RAG Pipeline...")
                self.advanced_pipeline = AdvancedRAGPipeline()
            
            if self.baseline_pipeline is None:
                self.logger.info("📊 Khởi tạo Baseline RAG Pipeline...")
                self.baseline_pipeline = BaselineRAGPipeline()
                
            self.logger.info("✅ Pipelines initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Lỗi khởi tạo pipelines: {e}")
            self.log_error("init", "pipeline_init", str(e))
            return False
    
    async def generate_answers_for_batch(self, batch_data, batch_idx):
        """Generate answers cho một batch với retry logic"""
        advanced_results = []
        baseline_results = []
        
        self.logger.info(f"📝 Generating answers for batch {batch_idx}...")
        
        for i, row in batch_data.iterrows():
            question = row.get("question_generated", "")
            ground_truth = row.get("best_answer_generated", "")
            
            if not question:
                continue
            
            # Retry logic cho từng question
            max_retries_per_question = 3
            retry_count = 0
            
            while retry_count < max_retries_per_question:
                try:
                    # Advanced pipeline
                    advanced_result = await self.advanced_pipeline.generate_answer(
                        question, f"adv-b{batch_idx}-{i}"
                    )
                    
                    # Baseline pipeline  
                    baseline_result = await self.baseline_pipeline.generate_answer(
                        question, f"base-b{batch_idx}-{i}"
                    )
                    
                    # Success - add results
                    advanced_results.append({
                        "question": question,
                        "answer": advanced_result["answer"],
                        "contexts": advanced_result["contexts"],
                        "ground_truth": ground_truth
                    })
                    
                    baseline_results.append({
                        "question": question,
                        "answer": baseline_result["answer"],
                        "contexts": baseline_result["contexts"],
                        "ground_truth": ground_truth
                    })
                    
                    # Rate limit protection
                    await asyncio.sleep(0.5)
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    
                    if "429" in error_msg or "rate limit" in error_msg.lower():
                        wait_time = min(60, 2 ** retry_count)  # Exponential backoff
                        self.logger.warning(f"⚠️ Rate limit hit, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    elif retry_count >= max_retries_per_question:
                        self.logger.error(f"❌ Failed question {i} in batch {batch_idx} after {max_retries_per_question} retries: {e}")
                        self.log_error(batch_idx, f"question_{i}", str(e))
                        break
                    else:
                        self.logger.warning(f"⚠️ Retry {retry_count}/{max_retries_per_question} for question {i}: {e}")
                        await asyncio.sleep(2)
        
        self.logger.info(f"✅ Batch {batch_idx}: {len(advanced_results)} advanced, {len(baseline_results)} baseline results")
        return advanced_results, baseline_results
    
    def evaluate_batch_with_ragas(self, advanced_results, baseline_results, batch_idx):
        """Đánh giá batch với RAGAS - với retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Convert to DataFrames then to RAGAS datasets
                advanced_df = pd.DataFrame(advanced_results)
                baseline_df = pd.DataFrame(baseline_results)
                
                # Convert to RAGAS format
                advanced_dataset = pandas_to_ragas(advanced_df)
                baseline_dataset = pandas_to_ragas(baseline_df)
                
                self.logger.info(f"⚡ Evaluating batch {batch_idx} với RAGAS (attempt {retry_count + 1})...")
                
                # Evaluate Advanced pipeline
                self.logger.info("  - Evaluating Advanced RAG...")
                advanced_scores = evaluate(
                    dataset=advanced_dataset,
                    llm=self.llm,
                    embeddings=self.embedding_model,
                    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                    run_config=self.run_config
                )
                
                # Small delay between evaluations
                time.sleep(5)
                
                # Evaluate Baseline pipeline
                self.logger.info("  - Evaluating Baseline RAG...")
                baseline_scores = evaluate(
                    dataset=baseline_dataset,
                    llm=self.llm,
                    embeddings=self.embedding_model,
                    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                    run_config=self.run_config
                )
                
                self.logger.info(f"✅ RAGAS evaluation completed for batch {batch_idx}")
                return advanced_scores, baseline_scores
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    wait_time = min(180, 30 * retry_count)  # Longer wait for RAGAS
                    self.logger.warning(f"⚠️ RAGAS rate limit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif retry_count >= max_retries:
                    self.logger.error(f"❌ RAGAS evaluation failed for batch {batch_idx} after {max_retries} retries")
                    self.log_error(batch_idx, "ragas_evaluation", str(e))
                    return None, None
                else:
                    self.logger.warning(f"⚠️ RAGAS retry {retry_count}/{max_retries}: {e}")
                    time.sleep(10)
        
        return None, None
    
    def save_batch_results(self, advanced_results, baseline_results, 
                          advanced_scores, baseline_scores, batch_idx):
        """Lưu kết quả batch vào 2 thư mục riêng biệt"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare Advanced RAG results
        if advanced_results and advanced_scores is not None:
            advanced_data = []
            adv_scores_df = advanced_scores.to_pandas()
            
            for i, result in enumerate(advanced_results):
                # Get RAGAS scores for this sample
                sample_scores = {}
                if i < len(adv_scores_df):
                    for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                        if metric in adv_scores_df.columns:
                            sample_scores[f'ragas_{metric}'] = adv_scores_df.iloc[i][metric]
                
                advanced_data.append({
                    'batch': batch_idx,
                    'sample_id': i + 1,
                    'question': result['question'],
                    'ground_truth': result['ground_truth'],
                    'retrieved_contexts': str(result['contexts']),  # Convert list to string
                    'contexts_count': len(result['contexts']),
                    'answer': result['answer'],
                    'answer_length': len(result['answer']),
                    'timestamp': timestamp,
                    **sample_scores  # Add all RAGAS scores
                })
            
            # Save Advanced RAG batch
            advanced_df = pd.DataFrame(advanced_data)
            advanced_file = os.path.join(self.advanced_dir, f"batch_{batch_idx:03d}_{timestamp}.xlsx")
            advanced_df.to_excel(advanced_file, index=False)
            print(f"✅ Saved Advanced RAG batch {batch_idx}: {advanced_file}")
        
        # Prepare Baseline RAG results
        if baseline_results and baseline_scores is not None:
            baseline_data = []
            base_scores_df = baseline_scores.to_pandas()
            
            for i, result in enumerate(baseline_results):
                # Get RAGAS scores for this sample
                sample_scores = {}
                if i < len(base_scores_df):
                    for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                        if metric in base_scores_df.columns:
                            sample_scores[f'ragas_{metric}'] = base_scores_df.iloc[i][metric]
                
                baseline_data.append({
                    'batch': batch_idx,
                    'sample_id': i + 1,
                    'question': result['question'],
                    'ground_truth': result['ground_truth'],
                    'retrieved_contexts': str(result['contexts']),  # Convert list to string
                    'contexts_count': len(result['contexts']),
                    'answer': result['answer'],
                    'answer_length': len(result['answer']),
                    'timestamp': timestamp,
                    **sample_scores  # Add all RAGAS scores
                })
            
            # Save Baseline RAG batch
            baseline_df = pd.DataFrame(baseline_data)
            baseline_file = os.path.join(self.baseline_dir, f"batch_{batch_idx:03d}_{timestamp}.xlsx")
            baseline_df.to_excel(baseline_file, index=False)
            print(f"✅ Saved Baseline RAG batch {batch_idx}: {baseline_file}")
        
        # Create and save comparison summary
        if advanced_results and baseline_results and advanced_scores is not None and baseline_scores is not None:
            summary_data = []
            adv_scores_df = advanced_scores.to_pandas()
            base_scores_df = baseline_scores.to_pandas()
            
            for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                if metric in adv_scores_df.columns and metric in base_scores_df.columns:
                    adv_mean = adv_scores_df[metric].mean()
                    base_mean = base_scores_df[metric].mean()
                    improvement = ((adv_mean - base_mean) / base_mean * 100) if base_mean > 0 else 0
                    
                    summary_data.append({
                        'metric': metric,
                        'advanced_score': adv_mean,
                        'baseline_score': base_mean,
                        'improvement_pct': improvement,
                        'batch': batch_idx,
                        'timestamp': timestamp
                    })
            
            # Save comparison summary
            summary_df = pd.DataFrame(summary_data)
            summary_file = os.path.join(self.output_dir, f"comparison_batch_{batch_idx:03d}_{timestamp}.xlsx")
            summary_df.to_excel(summary_file, index=False)
            
            # Print summary
            print(f"\n📈 BATCH {batch_idx} RAGAS COMPARISON:")
            print("-" * 60)
            for _, row in summary_df.iterrows():
                print(f"{row['metric']:<20}: Adv={row['advanced_score']:.4f}, Base={row['baseline_score']:.4f}, Δ={row['improvement_pct']:+.2f}%")
            
            return summary_df
        
        return None
    
    async def run_full_evaluation(self, batch_size=50, start_batch=0, end_batch=None):
        """Chạy full evaluation với error recovery và auto save"""
        # Load test data
        print("📊 Loading test dataset...")
        test_data = pd.read_excel("./data/generated_test_dataset_question_answers_best_answer_final.xlsx")
        
        total_samples = len(test_data)
        total_batches = (total_samples + batch_size - 1) // batch_size
        
        if end_batch is None:
            end_batch = total_batches
        
        print(f"📋 Dataset info:")
        print(f"  - Total samples: {total_samples}")
        print(f"  - Batch size: {batch_size}")
        print(f"  - Total batches: {total_batches}")
        print(f"  - Processing batches: {start_batch} to {end_batch-1}")
        
        # Progress tracking file
        progress_file = f"{self.output_dir}/progress.txt"
        completed_batches = set()
        
        # Load previous progress if exists
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        completed_batches = set(map(int, content.split('\n')))
                print(f"📄 Found previous progress: {len(completed_batches)} batches completed")
            except Exception as e:
                print(f"⚠️ Error reading progress file: {e}")
                completed_batches = set()
        
        # Initialize pipelines
        self.initialize_pipelines()
        
        # Process batches
        all_summaries = []
        successful_batches = 0
        
        for batch_idx in range(start_batch, min(end_batch, total_batches)):
            # Skip if batch already completed
            if batch_idx in completed_batches:
                print(f"⏭️ Batch {batch_idx + 1} already completed, skipping...")
                continue
                
            print(f"\n{'='*60}")
            print(f"🔄 PROCESSING BATCH {batch_idx + 1}/{total_batches}")
            print(f"Progress: {successful_batches}/{end_batch - start_batch} batches completed")
            print(f"{'='*60}")
            
            # Get batch data
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, total_samples)
            batch_data = test_data.iloc[start_idx:end_idx].copy()
            
            print(f"📄 Batch {batch_idx + 1}: samples {start_idx} to {end_idx-1} ({len(batch_data)} samples)")
            
            max_retries = 3
            retry_count = 0
            batch_success = False
            
            while retry_count < max_retries and not batch_success:
                try:
                    if retry_count > 0:
                        print(f"🔄 Retry {retry_count}/{max_retries} for batch {batch_idx + 1}")
                        await asyncio.sleep(30)  # Wait before retry
                    
                    # Generate answers
                    advanced_results, baseline_results = await self.generate_answers_for_batch(
                        batch_data, batch_idx + 1
                    )
                    
                    if not advanced_results or not baseline_results:
                        print(f"⚠️ Batch {batch_idx + 1}: Không có kết quả, retry...")
                        retry_count += 1
                        continue
                    
                    print(f"✅ Generated {len(advanced_results)} advanced và {len(baseline_results)} baseline answers")
                    
                    # Evaluate with RAGAS
                    advanced_scores, baseline_scores = self.evaluate_batch_with_ragas(
                        advanced_results, baseline_results, batch_idx + 1
                    )
                    
                    # Save results - LUÔN LUU dù RAGAS có lỗi
                    summary = self.save_batch_results(
                        advanced_results, baseline_results,
                        advanced_scores, baseline_scores, batch_idx + 1
                    )
                    
                    if summary is not None:
                        all_summaries.append(summary)
                    
                    # Mark batch as completed
                    completed_batches.add(batch_idx)
                    with open(progress_file, 'w') as f:
                        f.write('\n'.join(map(str, sorted(completed_batches))))
                    
                    successful_batches += 1
                    batch_success = True
                    
                    print(f"✅ Batch {batch_idx + 1} completed và đã lưu!")
                    
                    # Sleep between batches để tránh rate limit
                    if batch_idx < end_batch - 1:
                        print("😴 Nghỉ 15s trước batch tiếp theo...")
                        await asyncio.sleep(15)
                    
                except Exception as e:
                    retry_count += 1
                    print(f"❌ Lỗi xử lý batch {batch_idx + 1} (attempt {retry_count}): {e}")
                    if retry_count >= max_retries:
                        print(f"💀 Batch {batch_idx + 1} failed after {max_retries} retries, moving to next batch")
                        # Save error log
                        error_log = f"{self.output_dir}/error_log_batch_{batch_idx + 1}.txt"
                        with open(error_log, 'w') as f:
                            f.write(f"Batch {batch_idx + 1} failed after {max_retries} retries\n")
                            f.write(f"Error: {str(e)}\n")
                            f.write(f"Time: {datetime.now()}\n")
                    else:
                        await asyncio.sleep(60)  # Wait longer before retry
        
        # Create overall summary
        print(f"\n🎯 TẠO TỔNG KẾT CUỐI CÙNG...")
        print(f"📊 Completed {successful_batches}/{end_batch - start_batch} batches successfully")
        
        if all_summaries:
            overall_summary = pd.concat(all_summaries, ignore_index=True)
            
            # Calculate overall averages
            overall_stats = overall_summary.groupby(['metric']).agg({
                'advanced_score': 'mean',
                'baseline_score': 'mean',
                'improvement_pct': 'mean'
            }).reset_index()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            overall_stats.to_excel(f"{self.output_dir}/final_comparison_summary_{timestamp}.xlsx", index=False)
            overall_summary.to_excel(f"{self.output_dir}/all_batches_detailed_{timestamp}.xlsx", index=False)
            
            # Create consolidated files for each pipeline
            self.create_consolidated_files(timestamp)
            
            print(f"\n📈 TỔNG KẾT CUỐI CÙNG:")
            print("=" * 70)
            for _, row in overall_stats.iterrows():
                print(f"{row['metric']:<20}: Adv={row['advanced_score']:.4f}, Base={row['baseline_score']:.4f}, Δ={row['improvement_pct']:+.2f}%")
        else:
            print("⚠️ Không có summary nào được tạo")
        
        print(f"\n🎉 HOÀN TẤT! Kết quả đã lưu trong:")
        print(f"  📁 Advanced RAG: {self.advanced_dir}")
        print(f"  📁 Baseline RAG: {self.baseline_dir}")
        print(f"  📁 Comparisons: {self.output_dir}")
        print(f"📊 Final stats: {successful_batches}/{end_batch - start_batch} batches completed")
        
        # Final progress cleanup
        if successful_batches == (end_batch - start_batch):
            print("🏆 ALL BATCHES COMPLETED SUCCESSFULLY!")
        else:
            failed_batches = set(range(start_batch, end_batch)) - completed_batches
            print(f"⚠️ Failed batches: {sorted(failed_batches)}")
        
        # Create consolidated files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.create_consolidated_files(timestamp)
    
    def create_consolidated_files(self, timestamp):
        """Tạo file tổng hợp từ tất cả các batch"""
        try:
            # Consolidate Advanced RAG files
            advanced_files = [f for f in os.listdir(self.advanced_dir) if f.endswith('.xlsx')]
            if advanced_files:
                advanced_dfs = []
                for file in sorted(advanced_files):
                    df = pd.read_excel(os.path.join(self.advanced_dir, file))
                    advanced_dfs.append(df)
                
                consolidated_advanced = pd.concat(advanced_dfs, ignore_index=True)
                consolidated_advanced.to_excel(
                    os.path.join(self.output_dir, f"consolidated_advanced_all_batches_{timestamp}.xlsx"), 
                    index=False
                )
                print(f"✅ Consolidated Advanced RAG: {len(consolidated_advanced)} samples")
            
            # Consolidate Baseline RAG files
            baseline_files = [f for f in os.listdir(self.baseline_dir) if f.endswith('.xlsx')]
            if baseline_files:
                baseline_dfs = []
                for file in sorted(baseline_files):
                    df = pd.read_excel(os.path.join(self.baseline_dir, file))
                    baseline_dfs.append(df)
                
                consolidated_baseline = pd.concat(baseline_dfs, ignore_index=True)
                consolidated_baseline.to_excel(
                    os.path.join(self.output_dir, f"consolidated_baseline_all_batches_{timestamp}.xlsx"), 
                    index=False
                )
                print(f"✅ Consolidated Baseline RAG: {len(consolidated_baseline)} samples")
                
        except Exception as e:
            print(f"⚠️ Lỗi tạo file consolidated: {e}")

async def main():
    """Main function with better configuration"""
    evaluator = FullRAGEvaluator()
    
    # Cấu hình cho full run 6000 samples
    batch_size = 50
    start_batch = 0
    end_batch = 120  # 120 * 50 = 6000 samples
    
    print("🚀 FULL RAGAS EVALUATION - 6000 SAMPLES")
    print("=" * 60)
    print(f"⚙️ Cấu hình:")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Start batch: {start_batch}")
    print(f"  - End batch: {end_batch}")
    print(f"  - Total samples to process: {(end_batch - start_batch) * batch_size}")
    
    # Check for previous progress
    progress_file = f"{evaluator.output_dir}/progress.txt"
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            completed = f.read().strip().split('\n') if f.read().strip() else []
        print(f"📄 Previous progress found: {len([x for x in completed if x])} batches completed")
    
    # Confirm
    confirm = input("\n⚠️ Bạn có muốn tiếp tục? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Hủy evaluation.")
        return
    
    try:
        await evaluator.run_full_evaluation(
            batch_size=batch_size,
            start_batch=start_batch,
            end_batch=end_batch
        )
    except Exception as e:
        print(f"❌ Lỗi critical trong quá trình evaluation: {e}")
        import traceback
        traceback.print_exc()

# Test function with 5 samples
async def main():
    """Chạy full evaluation cho 6000 mẫu, 50 mẫu mỗi batch"""
    print("🚀 STARTING FULL RAGAS EVALUATION")
    print("="*60)
    print("📊 Dataset: 6000 samples")
    print("📦 Batch size: 50 samples/batch")
    print("🎯 Total batches: 120 batches")
    print("="*60)
    
    try:
        evaluator = FullRAGEvaluator()
        await evaluator.run_full_evaluation(
            batch_size=50,   # 50 mẫu mỗi batch
            start_batch=0,   # Bắt đầu từ batch 0
            end_batch=120    # 120 batches tổng cộng (6000/50)
        )
        print("\n🎉 HOÀN THÀNH TOÀN BỘ EVALUATION!")
    except Exception as e:
        print(f"❌ Lỗi trong quá trình evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
