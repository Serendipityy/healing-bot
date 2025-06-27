#!/usr/bin/env python3
"""
Optimized Healing Bot Runner with speed options
"""
import subprocess
import sys
import time
import signal
import os
import requests
import argparse
from pathlib import Path

class OptimizedHealingBot:
    def __init__(self, fast_mode=False):
        self.backend_process = None
        self.frontend_process = None
        self.project_root = Path(__file__).parent
        self.fast_mode = fast_mode
    
    def start_backend(self):
        """Start FastAPI backend server"""
        mode_text = "⚡ FAST MODE" if self.fast_mode else "🚀 FULL MODE"
        print(f"🔧 Starting Backend ({mode_text})...")
        
        # Set environment variable for fast mode
        env = os.environ.copy()
        if self.fast_mode:
            env["FAST_MODE"] = "true"
            print("  • Lazy loading enabled")
            print("  • Using summary retriever only")
            print("  • Skip heavy components until needed")
        
        backend_cmd = [
            sys.executable, "-m", "uvicorn", 
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload" if not self.fast_mode else "--no-reload",  # No reload in fast mode
            "--log-level", "warning" if self.fast_mode else "info"  # Less verbose in fast mode
        ]
        
        self.backend_process = subprocess.Popen(
            backend_cmd,
            cwd=self.project_root,
            env=env
        )
        
        # Different wait times based on mode
        max_wait = 15 if self.fast_mode else 30
        wait_interval = 1 if self.fast_mode else 2
        
        print(f"⏳ Waiting for backend ({max_wait}s max)...")
        
        for i in range(max_wait):
            try:
                time.sleep(wait_interval)
                response = requests.get("http://localhost:8000/health", timeout=3)
                if response.status_code == 200:
                    total_time = i * wait_interval
                    print(f"✅ Backend ready in {total_time}s!")
                    return True
            except requests.exceptions.ConnectionError:
                if i < max_wait - 1:
                    print(f"  ⏳ {i+1}/{max_wait}...")
                continue
            except Exception:
                continue
        
        print("❌ Backend failed to start")
        return False
    
    def start_frontend(self):
        """Start Streamlit frontend"""
        print("🎨 Starting Frontend...")
        
        frontend_cmd = [
            sys.executable, "-m", "streamlit", "run",
            "frontend/app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--logger.level", "warning"  # Less verbose
        ]
        
        self.frontend_process = subprocess.Popen(
            frontend_cmd,
            cwd=self.project_root,
            env=os.environ.copy()
        )
        
        time.sleep(3)
        
        if self.frontend_process.poll() is None:
            print("✅ Frontend ready!")
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
                self.backend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            print("✅ Backend stopped")
        
        if self.frontend_process:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            print("✅ Frontend stopped")
    
    def show_success_message(self):
        """Show success message with mode-specific info"""
        mode_name = "FAST MODE" if self.fast_mode else "FULL MODE"
        mode_icon = "⚡" if self.fast_mode else "🚀"
        
        print(f"\n{'='*60}")
        print(f"🎉 Healing Bot is running in {mode_icon} {mode_name}!")
        print("="*60)
        print("📱 Frontend: http://localhost:8501")
        print("🔧 Backend:  http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("="*60)
        
        if self.fast_mode:
            print("⚡ FAST MODE Features:")
            print("  • Quick startup (5-15 seconds)")
            print("  • Lazy loading of heavy components")
            print("  • Summary retriever only (faster responses)")
            print("  • Perfect for development and testing")
            print("  • Full components load on first chat message")
        else:
            print("🚀 FULL MODE Features:")
            print("  • Complete RAG pipeline")
            print("  • Both full and summary retrievers")
            print("  • All rerankers and filters enabled")
            print("  • Best quality responses")
            print("  • Production-ready performance")
        
        print("\n💡 Usage:")
        print("  1. Open http://localhost:8501")
        print("  2. Start chatting with the bot")
        print("  3. Press Ctrl+C here to stop")
        
        if self.fast_mode:
            print("\n⏱️  Note: First message may take extra time")
            print("    as full components load lazily")
        
        print("="*60)
    
    def run(self):
        """Run the application"""
        def signal_handler(signum, frame):
            self.stop_servers()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            if not self.start_backend():
                return
            
            if not self.start_frontend():
                self.stop_servers()
                return
            
            self.show_success_message()
            
            # Monitor processes
            while True:
                if self.backend_process.poll() is not None:
                    print("❌ Backend died")
                    break
                if self.frontend_process.poll() is not None:
                    print("❌ Frontend died")
                    break
                time.sleep(2)
        
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            self.stop_servers()

def main():
    parser = argparse.ArgumentParser(description="Healing Bot Runner")
    parser.add_argument(
        "--fast", 
        action="store_true", 
        help="Use fast mode (quick startup, lazy loading)"
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        help="Explicitly set mode (fast or full)"
    )
    
    args = parser.parse_args()
    
    # Determine mode
    fast_mode = args.fast or args.mode == "fast"
    
    print("🤗 Healing Bot - Optimized Runner")
    print("="*50)
    
    if fast_mode:
        print("⚡ Mode: FAST (Development)")
        print("  • Quick startup: ~5-15 seconds")
        print("  • Lazy loading enabled")
    else:
        print("🚀 Mode: FULL (Production)")
        print("  • Complete initialization: ~15-30 seconds")
        print("  • All features enabled")
    
    print("\n💡 Tips:")
    print("  • Use --fast for development")
    print("  • Use default for production")
    print("  • Add --help for options")
    print("="*50)
    
    # Check dependencies
    try:
        import fastapi, uvicorn, streamlit, aiosqlite
        print("✅ Dependencies OK")
    except ImportError as e:
        print(f"❌ Missing: {e}")
        print("💡 Run: pip install -r requirements_new.txt")
        return
    
    bot = OptimizedHealingBot(fast_mode=fast_mode)
    bot.run()

if __name__ == "__main__":
    main()
