#!/usr/bin/env python3
"""
🎯 FINAL DATABASE QUALITY ASSESSMENT
=====================================

Script tổng kết và đánh giá chất lượng database sau khi rebuild hoàn toàn.
Kiểm tra format, search quality, completeness, và sẵn sàng production.

Created: 2025-06-29
Author: AI Assistant  
"""

import logging
import sys
from datetime import datetime
from qdrant_client import QdrantClient
from ragbase.ingestor import Ingestor

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('database_quality_report.log')
    ]
)
logger = logging.getLogger(__name__)

def final_quality_assessment():
    """Đánh giá chất lượng cuối cùng của database rebuilt"""
    
    logger.info("🎯 FINAL DATABASE QUALITY ASSESSMENT")
    logger.info("="*70)
    logger.info(f"📅 Assessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔧 Assessment Version: 1.0")
    
    try:
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333, prefer_grpc=False)
        ingestor = Ingestor()
        
        # 1. BASIC STATISTICS
        logger.info("\n📊 1. DATABASE STATISTICS")
        logger.info("-" * 50)
        
        docs_info = client.get_collection("documents")
        summary_info = client.get_collection("summary")
        
        docs_count = docs_info.points_count
        summary_count = summary_info.points_count
        total_count = docs_count + summary_count
        
        logger.info(f"   🏗️  Documents Collection: {docs_count:,} points")
        logger.info(f"   📋 Summary Collection: {summary_count:,} points")
        logger.info(f"   🎯 Total Points: {total_count:,}")
        logger.info(f"   🧠 Vector Dimension: {docs_info.config.params.vectors.size}")
        logger.info(f"   📐 Distance Metric: {docs_info.config.params.vectors.distance}")
        
        # 2. SAMPLE QUALITY CHECK
        logger.info(f"\n🔍 2. SAMPLE QUALITY CHECK")
        logger.info("-" * 50)
        
        # Get random samples
        sample_result = client.search(
            collection_name="documents",
            query_vector=[0.0] * 1024,
            limit=50,
            with_payload=True
        )
        
        complete_docs = 0
        question_only = 0
        answers_only = 0
        best_marked = 0
        
        for hit in sample_result:
            content = hit.payload.get('page_content', '')
            has_question = "Question:" in content
            has_answers = "Answers:" in content
            has_best = "⭐ BEST" in content
            
            if has_question and has_answers and has_best:
                complete_docs += 1
            elif has_question and not has_answers:
                question_only += 1
            elif has_answers and not has_question:
                answers_only += 1
                
            if has_best:
                best_marked += 1
                
        logger.info(f"   📄 Complete Documents: {complete_docs}/50 ({complete_docs*2}%)")
        logger.info(f"   ❓ Question-only Chunks: {question_only}/50 ({question_only*2}%)")
        logger.info(f"   💬 Answer-only Chunks: {answers_only}/50 ({answers_only*2}%)")
        logger.info(f"   ⭐ Best Answer Marked: {best_marked}/50 ({best_marked*2}%)")
        
        # 3. SEARCH QUALITY TEST
        logger.info(f"\n🔍 3. SEARCH QUALITY TEST")
        logger.info("-" * 50)
        
        test_queries = [
            "tình yêu thất bại",
            "áp lực công việc", 
            "trầm cảm",
            "gia đình xa cách",
            "mục tiêu cuộc sống"
        ]
        
        total_score = 0
        query_count = len(test_queries)
        
        for query in test_queries:
            query_vector = ingestor.embeddings.embed_query(query)
            results = client.search(
                collection_name="documents",
                query_vector=query_vector,
                limit=3,
                with_payload=True
            )
            
            if results:
                top_score = results[0].score
                labels = results[0].payload.get('labels', 'N/A')
                total_score += top_score
                logger.info(f"   📝 '{query}': score={top_score:.3f}, labels={labels}")
            else:
                logger.info(f"   ❌ '{query}': No results")
        
        avg_score = total_score / query_count if query_count > 0 else 0
        logger.info(f"   🏆 Average Search Score: {avg_score:.3f}")
        
        # 4. FORMAT COMPLIANCE
        logger.info(f"\n✅ 4. FORMAT COMPLIANCE CHECK")
        logger.info("-" * 50)
        
        # Check format compliance
        format_compliant = complete_docs >= 25  # At least 50% complete
        search_quality = avg_score >= 0.85  # Good search scores
        best_marking = best_marked >= 10  # Good best answer marking
        
        logger.info(f"   📄 Format Compliance: {'✅ PASS' if format_compliant else '❌ FAIL'}")
        logger.info(f"   🔍 Search Quality: {'✅ PASS' if search_quality else '❌ FAIL'}")
        logger.info(f"   ⭐ Best Answer Marking: {'✅ PASS' if best_marking else '❌ FAIL'}")
        
        # 5. METADATA INTEGRITY
        logger.info(f"\n🗂️  5. METADATA INTEGRITY CHECK")
        logger.info("-" * 50)
        
        metadata_fields = ['labels', 'question', 'doc_id', 'num_answers', 'has_best_marking']
        field_coverage = {}
        
        for hit in sample_result[:20]:
            for field in metadata_fields:
                if field in hit.payload:
                    field_coverage[field] = field_coverage.get(field, 0) + 1
        
        for field, count in field_coverage.items():
            coverage = (count / 20) * 100
            logger.info(f"   📋 {field}: {count}/20 ({coverage:.0f}%)")
        
        # 6. FINAL ASSESSMENT
        logger.info(f"\n🎯 6. FINAL ASSESSMENT")
        logger.info("-" * 50)
        
        all_checks = [format_compliant, search_quality, best_marking]
        passed_checks = sum(all_checks)
        
        if passed_checks == len(all_checks):
            status = "🟢 EXCELLENT"
            recommendation = "Database is production-ready with high quality!"
        elif passed_checks >= len(all_checks) * 0.8:
            status = "🟡 GOOD"
            recommendation = "Database quality is good, minor optimizations possible."
        else:
            status = "🔴 NEEDS_IMPROVEMENT"
            recommendation = "Database needs further optimization before production."
            
        logger.info(f"   🏆 Overall Status: {status}")
        logger.info(f"   ✅ Checks Passed: {passed_checks}/{len(all_checks)}")
        logger.info(f"   📋 Recommendation: {recommendation}")
        
        # 7. SUMMARY REPORT
        logger.info(f"\n📄 7. SUMMARY REPORT")
        logger.info("=" * 70)
        logger.info(f"   📊 Total Documents: {total_count:,}")
        logger.info(f"   📄 Complete Format Rate: {complete_docs*2}%")
        logger.info(f"   🔍 Average Search Score: {avg_score:.3f}")
        logger.info(f"   ⭐ Best Answer Coverage: {best_marked*2}%")
        logger.info(f"   🎯 Production Status: {status}")
        logger.info(f"   💡 Next Steps: {recommendation}")
        
        logger.info(f"\n✅ ASSESSMENT COMPLETED SUCCESSFULLY!")
        logger.info(f"📝 Detailed log saved to: database_quality_report.log")
        
        return {
            'status': status,
            'total_documents': total_count,
            'complete_rate': complete_docs * 2,
            'search_quality': avg_score,
            'best_answer_coverage': best_marked * 2,
            'recommendation': recommendation
        }
        
    except Exception as e:
        logger.error(f"❌ Assessment failed: {str(e)}")
        return None

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎯 HEALING BOT DATABASE QUALITY ASSESSMENT")
    print("="*70)
    
    result = final_quality_assessment()
    
    if result:
        print(f"\n🎉 Assessment completed successfully!")
        print(f"📊 Status: {result['status']}")
        print(f"💡 {result['recommendation']}")
    else:
        print(f"\n❌ Assessment failed. Check logs for details.")
        sys.exit(1)
