#!/usr/bin/env python3
"""
Final version of server runner with improved stability
"""
import subprocess
import sys
import time
import signal
import os
import requests
from pathlib import Path

class HealingBotManager:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.project_root = Path(__file__).parent
    
    def start_backend(self):
        """Start FastAPI backend server"""
        print("🚀 Starting Backend (FastAPI)...")
        
        backend_cmd = [
            sys.executable, "-m", "uvicorn", 
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ]
        
        self.backend_process = subprocess.Popen(
            backend_cmd,
            cwd=self.project_root,
            env=os.environ.copy()
        )
        
        print("⏳ Waiting for backend to initialize (this may take 15-20 seconds)...")
        
        # Wait for RAG service to initialize (takes about 15 seconds)
        max_attempts = 30
        for i in range(max_attempts):
            try:
                time.sleep(2)
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Backend is healthy and ready!")
                    return True
            except requests.exceptions.ConnectionError:
                print(f"   Attempt {i+1}/{max_attempts}: Backend initializing...")
                continue
            except Exception as e:
                print(f"   Health check error: {e}")
                continue
        
        print("❌ Backend failed to start properly")
        return False
    
    def start_frontend(self):
        """Start Streamlit frontend"""
        print("🎨 Starting Frontend (Streamlit)...")
        
        frontend_cmd = [
            sys.executable, "-m", "streamlit", "run",
            "frontend/app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true"
        ]
        
        self.frontend_process = subprocess.Popen(
            frontend_cmd,
            cwd=self.project_root,
            env=os.environ.copy()
        )
        
        # Wait for frontend to start
        time.sleep(5)
        
        if self.frontend_process.poll() is None:
            print("✅ Frontend started successfully!")
            return True
        else:
            print("❌ Frontend failed to start")
            return False
    
    def stop_servers(self):
        """Stop both servers"""
        print("\n🛑 Stopping servers...")
        
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            print("✅ Backend stopped")
        
        if self.frontend_process:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            print("✅ Frontend stopped")
    
    def run(self):
        """Run both servers"""
        def signal_handler(signum, frame):
            self.stop_servers()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start backend
            if not self.start_backend():
                return
            
            # Start frontend
            if not self.start_frontend():
                self.stop_servers()
                return
            
            print("\n" + "="*60)
            print("🎉 Healing Bot is now running successfully!")
            print("="*60)
            print("📱 Frontend (Chat Interface): http://localhost:8501")
            print("🔧 Backend API:               http://localhost:8000")
            print("📚 API Documentation:         http://localhost:8000/docs")
            print("="*60)
            print("\n✨ Features of the new architecture:")
            print("  • Clean async handling with FastAPI")
            print("  • Separated Frontend/Backend")
            print("  • No more nest_asyncio complications")
            print("  • Better error handling and logging")
            print("  • Scalable and maintainable structure")
            print("\n🔥 Performance improvements:")
            print("  • Native async support")
            print("  • Streaming responses")
            print("  • Efficient resource management")
            print("\n💡 To use:")
            print("  1. Open http://localhost:8501 in your browser")
            print("  2. Start chatting with the healing bot")
            print("  3. View API docs at http://localhost:8000/docs")
            print("\n⚠️  Press Ctrl+C to stop both servers")
            print("="*60)
            
            # Keep running and monitor processes
            while True:
                if self.backend_process.poll() is not None:
                    print("❌ Backend process stopped unexpectedly")
                    break
                if self.frontend_process.poll() is not None:
                    print("❌ Frontend process stopped unexpectedly")
                    break
                time.sleep(2)
        
        except KeyboardInterrupt:
            print("\n👋 Gracefully shutting down...")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        finally:
            self.stop_servers()

def main():
    """Main entry point"""
    print("🤗 Healing Bot - Advanced Architecture")
    print("="*50)
    print("🔧 Initializing services...")
    
    # Check if required dependencies are available
    try:
        import fastapi, uvicorn, streamlit, aiosqlite
        print("✅ All dependencies are available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Please run: pip install -r requirements_new.txt")
        return
    
    manager = HealingBotManager()
    manager.run()

if __name__ == "__main__":
    main()
