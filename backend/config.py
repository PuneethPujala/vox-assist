from pydantic_settings import BaseSettings, SettingsConfigDict
import os

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "voxassist"
    FIREBASE_CREDENTIALS_PATH: str = "service-account-key.json"
    SECRET_KEY: str = "default_secret"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
    ]
    FRONTEND_URL: str = "http://localhost:5173"
    MAX_PROMPT_LENGTH: int = 5000

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        extra="ignore"
    )


settings = Settings()