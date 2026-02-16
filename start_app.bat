@echo off
echo Starting VOX-ASSIST System...

:: Start Backend
echo Starting Backend...
start "VOX-ASSIST Backend" cmd /k "call venv\Scripts\activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

:: Start Frontend
echo Starting Frontend...
cd frontend
:: Ensure dependencies are installed if missing
:: Check for Vite binary
if not exist "node_modules\vite\bin\vite.js" (
    echo Vite module not found. Installing dependencies...
    call npm install
)

:: Use the direct runner which works better with the current environment
echo Starting Frontend (Direct Mode)...
start "VOX-ASSIST Frontend" cmd /k "..\run_vite_direct.bat"

echo System started. Close the popup windows to stop servers.
pause
