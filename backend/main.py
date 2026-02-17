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

from fastapi.staticfiles import StaticFiles

app.include_router(api_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")

# Mount static files
os.makedirs("backend/static", exist_ok=True)
app.mount("/assets", StaticFiles(directory="backend/static/assets"), name="assets")

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

from fastapi.responses import FileResponse

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # API routes are already handled by the routers above.
    # If the path is not an API route (checked by order of inclusion)
    # serve the index.html
    return FileResponse("backend/static/index.html")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
# Force reload trigger 30
