"""
Shared pytest fixtures for Football Predictor backend tests.
"""

import os
import sys
import asyncio
import pytest
import pandas as pd
import numpy as np

# ── Ensure backend is importable ──────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Prevent actual model loading from environment ─────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_football.db")
os.environ.setdefault("MODEL_CACHE_DIR", "/tmp/test_model_cache")
os.environ.setdefault("LOG_LEVEL", "ERROR")  # quieten logs during tests


@pytest.fixture
def sample_match_df() -> pd.DataFrame:
    """Generate synthetic match history (80 matches) for testing."""
    np.random.seed(42)
    n = 80
    teams = ["Arsenal", "Chelsea", "Liverpool", "Manchester City",
             "Tottenham", "Manchester United", "Newcastle", "Aston Villa"]
    rows = []
    for i in range(n):
        home, away = teams[i % len(teams)], teams[(i + 3) % len(teams)]
        home_goals = int(np.random.poisson(1.4))
        away_goals = int(np.random.poisson(1.1))
        rows.append({
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i * 3),
            "home_team": home, "away_team": away,
            "home_goals": home_goals, "away_goals": away_goals,
            "home_ht_goals": max(0, home_goals - np.random.randint(0, 2)),
            "away_ht_goals": max(0, away_goals - np.random.randint(0, 2)),
            "home_shots_on_target": int(np.random.poisson(5)),
            "away_shots_on_target": int(np.random.poisson(4)),
            "competition": "PL",
            "status": "FINISHED",
        })
    return pd.DataFrame(rows)


@pytest.fixture
def trained_predictor(sample_match_df):
    """Return a predictor trained on sample data."""
    from models.linear_regression import FootballPredictor
    predictor = FootballPredictor()
    predictor.train(sample_match_df)
    return predictor


@pytest.fixture
def prediction_payload():
    """Standard prediction request payload dict."""
    return {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_team_id": None,
        "away_team_id": None,
        "competition_code": "PL",
        "home_lineup": [],
        "away_lineup": [],
        "home_subs": [],
        "away_subs": [],
        "home_position": 3,
        "away_position": 5,
        "match_importance": 1.0,
        "data_source": "api",
        "csv_data": None,
    }


@pytest.fixture
def mock_csv_rows():
    """Minimal CSV data rows matching football-data.co.uk format."""
    return [
        {"HomeTeam": "Arsenal", "AwayTeam": "Chelsea",
         "FTHG": "2", "FTAG": "1", "HTHG": "1", "HTAG": "0",
         "HST": "6", "AST": "4", "Date": "01/08/2024"},
        {"HomeTeam": "Liverpool", "AwayTeam": "ManCity",
         "FTHG": "1", "FTAG": "1", "HTHG": "0", "HTAG": "1",
         "HST": "5", "AST": "7", "Date": "02/08/2024"},
    ] * 20  # 40 rows total (need MIN_MATCHES_FOR_TRAINING=30)
