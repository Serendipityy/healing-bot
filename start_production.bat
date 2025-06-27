@echo off
echo Starting Healing Bot in PRODUCTION mode...
echo This provides EXCELLENT quality with Full+Summary data, Reranker, and optimizations

set RAG_MODE=production
python run_healing_bot.py

pause
