# VOX-ASSIST

AI-Powered Architectural Layout Generator

## Project Structure

- **frontend/**: React + Vite application (User Interface)
- **backend/**: FastAPI application (API & Logic)
  - **engine/**: The core ML layout generation engine (from ResPlan)
  - **services/**: Service layer wrapping the engine
  - **routes/**: API endpoints

## Setup

1. **Backend Environment**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r backend/requirements.txt
```

2. **Frontend Dependencies**
```powershell
cd frontend
npm install
```

3. **Environment Variables**
Copy `backend/.env.example` to `backend/.env` and update credentials.

## Running the Application

### Option 1: Development Script (Windows)

Run the PowerShell script to start both servers:
```powershell
.\run_dev.ps1
```

### Option 2: Manual Start

**Backend**:
```powershell
.\venv\Scripts\uvicorn backend.main:app --reload --port 8000
```

**Frontend**:
```powershell
cd frontend
npm run dev
```

Key features:
- Connects to MongoDB (ensure it's running)
- Uses Firebase Auth (configure in .env)
- Generates layouts using ResPlan engine
