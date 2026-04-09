import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import FRONTEND_URL, BACKEND_API_KEY, MODEL_CACHE_FILE
from logger import get_logger, set_request_id
from database import init_db
from routers import predictions, teams, upload
from routers.predictions import _predictor, FootballPredictor
from services.football_api import football_api

logger = get_logger(__name__)

# ── Rate limiter (shared state) ───────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("⚽ Football Predictor API starting up…")

    # 1. Initialize database (create tables if not exists)
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.error("Database init failed: %s", exc)

    # 2. Load cached model if available
    cache_path = Path(MODEL_CACHE_FILE)
    if cache_path.exists():
        try:
            loaded = FootballPredictor.load_model()
            # Patch the module-level singleton in predictions router
            import routers.predictions as pred_module
            pred_module._predictor = loaded
            logger.info(
                "Loaded cached model from %s (samples=%d)",
                MODEL_CACHE_FILE, loaded.training_samples
            )
        except Exception as exc:
            logger.warning("Could not load cached model: %s — will train on demand", exc)
    else:
        logger.info("No cached model found at %s — will train on first request", MODEL_CACHE_FILE)

    yield

    # Cleanup
    await football_api.close()
    logger.info("⚽ Football Predictor API shut down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Football Predictor API",
    description="Full-stack football match prediction engine using XGBoost + Poisson models",
    version="2.0.0",
    lifespan=lifespan,
)

# Rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing and request-ID."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    start = time.perf_counter()

    logger.info(
        "→ %s %s  client=%s",
        request.method, request.url.path,
        request.client.host if request.client else "unknown"
    )

    response: Response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "← %s %s  status=%d  %.1fms",
        request.method, request.url.path,
        response.status_code, elapsed_ms
    )

    response.headers["X-Request-ID"] = request_id
    return response


# ── Optional API key auth middleware ──────────────────────────────────────────

_OPEN_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """If BACKEND_API_KEY is configured, enforce it on all protected endpoints."""
    if not BACKEND_API_KEY:
        return await call_next(request)

    # Always allow health/docs/root
    if request.url.path in _OPEN_PATHS or request.url.path.startswith("/docs"):
        return await call_next(request)

    # Check header or query-param
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if key != BACKEND_API_KEY:
        logger.warning(
            "Unauthorized request to %s from %s",
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key. Provide X-API-Key header."},
        )

    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(predictions.router)
app.include_router(teams.router)
app.include_router(upload.router)


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "app": "Football Predictor API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "model_trained": _predictor.is_trained}
