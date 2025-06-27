@echo off
echo 🤗 Healing Bot - Quick Launcher
echo.

REM Check if we have arguments
if "%1"=="fast" goto FAST_MODE
if "%1"=="full" goto FULL_MODE
if "%1"=="help" goto SHOW_HELP

:CHOOSE_MODE
echo Please choose a mode:
echo.
echo [1] ⚡ FAST MODE - Quick startup (5-15 seconds)
echo     • Perfect for development and testing
echo     • Lazy loading of components
echo     • Summary retriever only
echo.
echo [2] 🚀 FULL MODE - Complete system (15-30 seconds)  
echo     • Production-ready performance
echo     • All retrievers and rerankers
echo     • Best response quality
echo.
echo [3] ❓ Help - Show more options
echo.
set /p choice="Enter your choice (1/2/3): "

if "%choice%"=="1" goto FAST_MODE
if "%choice%"=="2" goto FULL_MODE
if "%choice%"=="3" goto SHOW_HELP
echo Invalid choice. Please try again.
goto CHOOSE_MODE

:FAST_MODE
echo.
echo ⚡ Starting in FAST MODE...
python run_optimized.py --fast
goto END

:FULL_MODE
echo.
echo 🚀 Starting in FULL MODE...
python run_optimized.py
goto END

:SHOW_HELP
echo.
echo 🤗 Healing Bot - Usage Options
echo ===============================
echo.
echo Direct commands:
echo   start.bat fast    - Start in fast mode
echo   start.bat full    - Start in full mode
echo   start.bat help    - Show this help
echo.
echo Manual commands:
echo   python run_optimized.py --fast    - Fast mode
echo   python run_optimized.py           - Full mode
echo   python run_optimized.py --help    - Command help
echo.
echo Modes comparison:
echo   FAST: Quick startup, lazy loading, good for development
echo   FULL: Complete system, all features, production-ready
echo.
pause
goto END

:END
