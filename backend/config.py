import os
from dotenv import load_dotenv

load_dotenv()

# ── External API keys ─────────────────────────────────────────────────────────
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = os.getenv("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")

# ── App URLs ──────────────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Optional backend API key auth ─────────────────────────────────────────────
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY", "")  # if set, all endpoints require it

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./data/football_predictor.db"
)

# ── Redis / Cache ─────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")  # empty → fakeredis fallback
API_CACHE_TTL_SECONDS = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FORMAT = os.getenv("LOG_FORMAT", "text")   # "json" | "text"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "./logs/app.log")

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL_RETRAIN_ON_CSV = os.getenv("MODEL_RETRAIN_ON_CSV", "true").lower() == "true"
MIN_MATCHES_FOR_TRAINING = int(os.getenv("MIN_MATCHES_FOR_TRAINING", "30"))
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./model_cache")
MODEL_CACHE_FILE = os.path.join(MODEL_CACHE_DIR, "predictor_v1.joblib")
MODEL_METADATA_FILE = os.path.join(MODEL_CACHE_DIR, "metadata.json")

# ── Rate limiting (external API) ──────────────────────────────────────────────
API_RATE_LIMIT_PER_MINUTE = 10

# ── ML feature defaults ───────────────────────────────────────────────────────
DEFAULT_ROLLING_WINDOW_SHORT = 5
DEFAULT_ROLLING_WINDOW_LONG = 10
MAX_CORRECT_SCORE = 5
