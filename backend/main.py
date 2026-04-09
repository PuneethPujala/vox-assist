import torch  # Pre-load torch at module level to prevent DLL init failure on Windows
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
    # Startup: Fast DB connection
    await connect_to_mongo()
    
    # Offload slow index creation to background
    import asyncio
    asyncio.create_task(create_database_indexes())

    # Load Whisper in a thread — avoids Windows DLL/asyncio conflict
    try:
        print("[STARTUP] 🎙️  Loading Whisper model (base.en) in background thread...")
        import whisper
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            app.state.whisper_model = await loop.run_in_executor(
                pool, lambda: whisper.load_model("base.en")
            )
        print("[STARTUP] ✅  Whisper model loaded successfully.")
    except Exception as e:
        print(f"[STARTUP] ❌  ERROR — Failed to load Whisper model: {str(e)}")
        print("[STARTUP] ⚠️  Voice transcription will fallback to per-request loading.")
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

os.makedirs("static/models", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to VOX-ASSIST API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "vox-assist-backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)