"""Shared configuration: DB engine, RNG seed, study constants."""

import os
from datetime import date
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.environ["CLINOPS_DB_URL"]
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# Reproducible RNG
SEED = 42
rng = np.random.default_rng(SEED)

# Study timeline
STUDY_START = date(2024, 3, 1)
SNAPSHOT_DATE = date(2025, 9, 30)
STUDY_WEEKS = (SNAPSHOT_DATE - STUDY_START).days // 7  # ~82 weeks

# Protocol root
PROTOCOL_DIR = Path(__file__).resolve().parents[1] / "protocol"
