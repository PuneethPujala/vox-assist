# Contributing to VoxAssist

Thank you for your interest in contributing to VoxAssist!

## Tech Stack
- **Frontend:** React, Vite, Tailwind CSS, Three.js (React Three Fiber)
- **Backend:** FastAPI, Motor (Async MongoDB), Shapely, CV2
- **Database:** MongoDB
- **Auth:** Firebase

## Development Setup

### Backend
1. Ensure Python 3.10+ is installed.
2. Navigate to `backend/`.
3. Create a `.env` file from `.env.example`.
4. Run `pip install -r requirements.txt`.
5. Run the server using `uvicorn main:app --reload`.

### Frontend
1. Navigate to `frontend/`.
2. Create `.env` using your Firebase config.
3. Run `npm install` and `npm run dev`.

## Pull Request Process
1. Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2. Update the README.md with details of changes to the interface.
3. You may merge the Pull Request in once you have the sign-off of an administrator.
