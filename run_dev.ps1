$ErrorActionPreference = "Stop"

# Backend
$uvicornPath = ".\venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicornPath)) {
    Write-Host "Error: uvicorn.exe not found at $uvicornPath" -ForegroundColor Red
    Write-Host "Please run: .\venv\Scripts\pip install uvicorn fastapi"
    exit 1
}

$backend = Start-Process -FilePath $uvicornPath -ArgumentList "backend.main:app --reload --port 8000" -PassThru -NoNewWindow
Write-Host "Backend started with PID $($backend.Id)" -ForegroundColor Green

# Frontend
Set-Location frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "Error: node_modules not found in frontend" -ForegroundColor Red
    Write-Host "Please run: cd frontend; npm install"
    Stop-Process -Id $backend.Id -Force
    exit 1
}

# Use npm.cmd directly
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -PassThru -NoNewWindow
Write-Host "Frontend started with PID $($frontend.Id)" -ForegroundColor Green

Write-Host "Press any key to stop servers..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Stop-Process -Id $backend.Id -Force
Stop-Process -Id $frontend.Id -Force
Write-Host "Servers stopped."
