import os
import sys

# Ensure the backend directory is on sys.path so local imports work
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Heavy ML imports (torch, etc.) are deferred to prevent Render deployment timeouts.
# On Windows, we may still need a top-level torch import for some DLL initialization, 
# but for Render (Linux), doing it top-level causes 'Port scan timeout'.
if sys.platform == "win32":
    try:
        import torch
    except ImportError:
        pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes import api, user
from database.connection import connect_to_mongo, close_mongo_connection, create_database_indexes
import database.connection
from utils.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os
import sys
import logging

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    async def init_db():
        # Complete MongoDB startup in background
        await connect_to_mongo()
        await create_database_indexes()

    # Offload DB init to background to prevent blocking Render deployment
    asyncio.create_task(init_db())

    # Voice transcription model will be loaded lazily on the first request 
    # to avoid locking the Global Interpreter Lock (GIL) and timing out Render's health check.
    app.state.whisper_model = None

    yield
    
    # Shutdown
    await close_mongo_connection()
    print("[SHUTDOWN] 🛑  Whisper model released from memory.")
# --- Everything below is unchanged ---

app = FastAPI(
    title="VoxAssist Backend Core",
    description="The underlying compute and orchestration API serving the VoxAssist AI generator platform.",
    version="2.0.0",
    lifespan=lifespan,
    contact={
        "name": "VoxAssist Developer Support",
        "email": "support@voxassist.com",
    }
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "message": "Internal Server Error"}
    )

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://vox-assist.vercel.app",
    "https://vox-assist-pearl.vercel.app",
    "https://vox-assist-frontend.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")

os.makedirs("backend/static/models", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to VOX-ASSIST API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "vox-assist-backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)