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

    # Database - use EXTERNAL_DATABASE_URL from environment if available
    external_database_url: str = ""

    # Gemini - direct API key (set GEMINI_API_KEY in .env)
    gemini_api_key: str = ""
    # Gemini - Replit AI Integrations (automatically set by Replit)
    ai_integrations_gemini_api_key: str = ""
    ai_integrations_gemini_base_url: str = ""
    gemini_temperature: float = 0.0
    gemini_top_p: float = 0.95
    gemini_max_output_tokens: int = 8192
    gemini_max_retries: int = 3
    gemini_timeout: int = 600

    # Azure OpenAI (all values MUST be set in .env)
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_model_name: str = ""
    azure_openai_api_version: str = ""
    azure_openai_max_tokens: int = 16384

    # Model settings (override in .env)
    primary_llm: str = ""
    embedding_model: str = ""

    # Vector store
    chroma_persist_path: str = "data/vectorstore/chroma_db"

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./tmp"

    # CORS - allow all origins for development
    cors_origins: list[str] = ["*"]

    # Server
    backend_port: int = 8000

    # Database connection pool
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Operational thresholds (override in .env) ──
    # Query aging buckets (days)
    query_aging_amber_days: int = 14
    query_aging_red_days: int = 30

    # Attention site thresholds
    attention_open_query_threshold: int = 15
    attention_open_query_critical: int = 25
    attention_entry_lag_threshold: float = 5.0

    # Site status classification
    status_critical_open_queries: int = 20
    status_critical_alert_count: int = 2
    status_warning_open_queries: int = 10
    status_warning_enrollment_pct: float = 50.0

    # Data quality score formula: max(0, dq_score_base - (open_queries * dq_score_penalty))
    dq_score_base: int = 100
    dq_score_penalty_per_query: int = 5

    # Site detail thresholds
    site_entry_lag_elevated: float = 5.0
    site_open_queries_warning: int = 10
    site_open_queries_high: int = 15
    site_enrollment_below_target_pct: float = 75.0
    site_enrollment_trend_up_pct: float = 75.0
    site_lag_trend_delta: float = 2.0

    # Investigation thresholds (agents.py investigate endpoint)
    investigate_open_queries_action: int = 10
    investigate_open_queries_elevated: int = 15
    investigate_pass_rate_low_pct: float = 50.0
    investigate_confidence_base: float = 70.0
    investigate_confidence_per_point: float = 5.0
    investigate_confidence_max: float = 95.0

    # Tool thresholds
    narrative_fetch_limit: int = 200
    trend_stable_slope_factor: float = 0.01

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def db_url(self) -> str:
        """Get database URL, preferring EXTERNAL_DATABASE_URL env var."""
        return self.external_database_url


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Database engine and session factory
_settings = get_settings()
engine = create_engine(
    _settings.db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
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
