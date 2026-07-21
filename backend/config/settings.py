"""
CalRetail — FastAPI Application Settings
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "CalRetail Retail AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./calretail.db"
    DATA_PROCESSED_DIR: str = str(Path(__file__).parent.parent.parent / "data" / "processed")
    DATA_MODELS_DIR: str = str(Path(__file__).parent.parent.parent / "data" / "models")
    SECRET_KEY: str = "calretail-secret-key-change-in-production"
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
