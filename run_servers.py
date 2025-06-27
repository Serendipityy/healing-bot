#!/usr/bin/env python3
"""
Script to run both backend and frontend servers
"""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

class ServerManager:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.project_root = Path(__file__).parent
    
    def start_backend(self):
        """Start FastAPI backend server"""
        print("🚀 Starting Backend (FastAPI)...")
        
        # Change to project root directory
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
            env=os.environ.copy()  # Preserve environment variables
        )
        
        # Wait a moment for backend to start
        time.sleep(8)  # Increased from 5 to 8 seconds since RAG service takes time
        
        if self.backend_process.poll() is None:
            print("✅ Backend started successfully on http://localhost:8000")
        else:
            print("❌ Backend failed to start")
            print("Check if all dependencies are installed and Qdrant is running")
            return False
        
        return True
    
    def start_frontend(self):
        """Start Streamlit frontend"""
        print("🎨 Starting Frontend (Streamlit)...")
        
        frontend_cmd = [
            sys.executable, "-m", "streamlit", "run",
            "frontend/app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ]
        
        self.frontend_process = subprocess.Popen(
            frontend_cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        time.sleep(3)
        
        if self.frontend_process.poll() is None:
            print("✅ Frontend started successfully on http://localhost:8501")
        else:
            print("❌ Frontend failed to start")
            return False
        
        return True
    
    def check_health(self):
        """Check if backend is healthy"""
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            return response.status_code == 200
        except Exception:
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
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start backend
            if not self.start_backend():
                return
            
            # Check backend health
            print("⏳ Checking backend health...")
            for i in range(20):  # Increased from 10 to 20 attempts
                if self.check_health():
                    print("✅ Backend is healthy")
                    break
                print(f"   Attempt {i+1}/20: Backend not ready yet...")
                time.sleep(2)  # Wait 2 seconds between attempts
            else:
                print("❌ Backend health check failed")
                self.stop_servers()
                return
            
            # Start frontend
            if not self.start_frontend():
                self.stop_servers()
                return
            
            print("\n" + "="*50)
            print("🎉 Healing Bot is running!")
            print("📱 Frontend: http://localhost:8501")
            print("🔧 Backend API: http://localhost:8000")
            print("📚 API Docs: http://localhost:8000/docs")
            print("="*50)
            print("\nPress Ctrl+C to stop both servers")
            
            # Keep the script running
            while True:
                if self.backend_process.poll() is not None:
                    print("❌ Backend process died")
                    break
                if self.frontend_process.poll() is not None:
                    print("❌ Frontend process died")
                    break
                time.sleep(1)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_servers()

def main():
    """Main entry point"""
    print("🤗 Healing Bot Server Manager")
    print("Setting up the servers...")
    
    manager = ServerManager()
    manager.run()

if __name__ == "__main__":
    main()
