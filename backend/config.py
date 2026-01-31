"""Pydantic Settings and database configuration for the backend."""

import logging
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Resolve .env path relative to this file (backend/config.py -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Database
    clinops_db_url: str = "postgresql://angshuman.deb@localhost:5432/clinops_intel"

    # Gemini
    gemini_api_key: str = ""
    gemini_temperature: float = 0.0
    gemini_top_p: float = 0.95
    gemini_max_output_tokens: int = 50000
    gemini_max_retries: int = 3
    gemini_timeout: int = 300

    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = "https://pm-tst.openai.azure.com/"
    azure_openai_deployment: str = "gpt-5.2"
    azure_openai_model_name: str = "gpt-5.2"
    azure_openai_api_version: str = "2025-04-01-preview"

    # Model settings
    primary_llm: str = "gemini-3-pro-preview"
    embedding_model: str = "text-embedding-004"

    # Vector store
    chroma_persist_path: str = "data/vectorstore/chroma_db"

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./tmp"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Database engine and session factory
_settings = get_settings()
engine = create_engine(
    _settings.clinops_db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def setup_backend_logging():
    """Configure logging to ./tmp/ directory."""
    log_dir = Path(_settings.log_dir)
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, _settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "backend.log"),
        ],
        force=True,
    )
