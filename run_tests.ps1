$ErrorActionPreference = "Stop"

Write-Host "Running Backend Tests..."
.\venv\Scripts\python test_imports.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Backend Imports Pass" -ForegroundColor Green
} else {
    Write-Host "❌ Backend Imports Fail" -ForegroundColor Red
    exit 1
}

Write-Host "Checking Frontend Build..."
Set-Location frontend
npm run build
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Frontend Build Pass" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend Build Fail" -ForegroundColor Red
    exit 1
}

Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
