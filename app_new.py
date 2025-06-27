"""
New Healing Bot App - Clean architecture with separated backend and frontend
Run this with: python run_servers.py
"""

# This file is kept for compatibility but the new architecture uses:
# - backend/main.py for FastAPI backend
# - frontend/app.py for Streamlit frontend  
# - run_servers.py to run both

print("""
🤗 Healing Bot - New Architecture

This project has been refactored with a clean separation of concerns:

📁 Backend (FastAPI):
   └── backend/main.py - Main FastAPI application
   └── backend/services/ - Business logic services  
   └── backend/models/ - Pydantic models
   └── backend/config/ - Configuration

📁 Frontend (Streamlit):
   └── frontend/app.py - Streamlit UI
   └── frontend/api_client.py - HTTP client for backend
   └── frontend/ui_components.py - UI components

🚀 To run the application:
   python run_servers.py

This will start both:
- Backend API server on http://localhost:8000
- Frontend UI on http://localhost:8501

✨ Benefits:
- No more nest_asyncio complications
- Clean async handling with FastAPI
- Separated frontend and backend
- Better error handling
- Scalable architecture
""")

# For backwards compatibility, you can still run the old version:
if __name__ == "__main__":
    import subprocess
    import sys
    
    choice = input("\nDo you want to run the NEW architecture? (y/n): ").lower().strip()
    
    if choice in ['y', 'yes']:
        print("🚀 Starting new architecture...")
        subprocess.run([sys.executable, "run_servers.py"])
    else:
        print("Running old version (not recommended)...")
        # Import and run old app here if needed
        import streamlit as st
        st.write("Please use the new architecture: `python run_servers.py`")
