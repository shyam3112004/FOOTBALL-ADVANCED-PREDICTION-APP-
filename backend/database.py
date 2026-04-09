"""
Async SQLAlchemy database setup for Football Predictor.

Tables:
  - predictions  : individual match prediction records
  - training_runs: model training history

DB file: ./data/football_predictor.db  (overrideable via DATABASE_URL)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import (
    Column, DateTime, Integer, String, Text, Float, text
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL

# ── Ensure data directory exists ──────────────────────────────────────────────
if DATABASE_URL.startswith("sqlite"):
    _db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

# ── Engine & Session ──────────────────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── ORM Models ────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(String(36), unique=True, nullable=False, index=True)
    batch_id = Column(String(36), nullable=True, index=True)
    home_team = Column(String(200), nullable=False)
    away_team = Column(String(200), nullable=False)
    competition = Column(String(50), nullable=True)
    match_date = Column(String(30), nullable=True)
    payload_json = Column(Text, nullable=True)   # serialised request
    result_json = Column(Text, nullable=False)   # serialised prediction result
    model_confidence = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "batch_id": self.batch_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "competition": self.competition,
            "match_date": self.match_date,
            "model_confidence": self.model_confidence,
            "result": json.loads(self.result_json) if self.result_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    samples = Column(Integer, nullable=False)
    metrics_json = Column(Text, nullable=True)  # serialised metrics dict
    model_path = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "samples": self.samples,
            "metrics": json.loads(self.metrics_json) if self.metrics_json else {},
            "model_path": self.model_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── Init ──────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables (safe to call on every startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable WAL mode for SQLite (better concurrency)
        if "sqlite" in DATABASE_URL:
            await conn.execute(text("PRAGMA journal_mode=WAL"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
