from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "voxassist"
    FIREBASE_CREDENTIALS_PATH: str = "service-account-key.json"
    SECRET_KEY: str = "default_secret"
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:4173"]'
    FRONTEND_URL: str = "http://localhost:5173"
    
    class Config:
        env_file = "backend/.env"

settings = Settings()
