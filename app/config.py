import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base project directory (d:\voice)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # API Keys
    HUGGINGFACE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # Whisper STT
    WHISPER_MODEL_SIZE: str = "base"
    
    # Storage Paths
    DOCUMENTS_DIR: Path = PROJECT_ROOT / "data" / "documents"
    VECTOR_DB_DIR: Path = PROJECT_ROOT / "data" / "vector_db"
    TEMP_AUDIO_DIR: Path = PROJECT_ROOT / "data" / "temp_audio"
    
    # Server config
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG_MODE: bool = True
    DEFAULT_LANGUAGE: str = "hi"  # 'hi' for Hindi, 'en' for English

    class Config:
        env_file = str(BACKEND_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
