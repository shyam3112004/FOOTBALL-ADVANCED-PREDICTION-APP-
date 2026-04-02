import os
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = os.getenv("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MODEL_RETRAIN_ON_CSV = os.getenv("MODEL_RETRAIN_ON_CSV", "true").lower() == "true"
MIN_MATCHES_FOR_TRAINING = int(os.getenv("MIN_MATCHES_FOR_TRAINING", "30"))

# Rate limiting
API_RATE_LIMIT_PER_MINUTE = 10
API_CACHE_TTL_SECONDS = 300  # 5 minutes

# ML defaults
DEFAULT_ROLLING_WINDOW_SHORT = 5
DEFAULT_ROLLING_WINDOW_LONG = 10
MAX_CORRECT_SCORE = 5
