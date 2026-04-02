from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import FRONTEND_URL
from routers import predictions, teams, upload
from services.football_api import football_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    print("⚽ Football Predictor API starting up...")
    yield
    # Cleanup
    await football_api.close()
    print("⚽ Football Predictor API shut down.")


app = FastAPI(
    title="Football Predictor API",
    description="Full-stack football match prediction engine using Linear Regression + Poisson models",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(predictions.router)
app.include_router(teams.router)
app.include_router(upload.router)


@app.get("/")
async def root():
    return {
        "app": "Football Predictor API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
