from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.api import router as api_router
from backend.routes.user import router as user_router
from backend.database.connection import connect_to_mongo, close_mongo_connection
import uvicorn
import os

app = FastAPI(title="VOX-ASSIST API")

# Helper to load env for CORS
# For now, allowing all for development
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

app.include_router(api_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")

# Mount static files
os.makedirs("backend/static/models", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

@app.get("/")
def read_root():
    return {"message": "Welcome to VOX-ASSIST API"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
# Force reload trigger 30
