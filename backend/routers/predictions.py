import json
import re
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator, model_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import io

from models.linear_regression import FootballPredictor
from services.football_api import football_api
from services.csv_parser import csv_parser
from services.excel_exporter import excel_exporter
from database import get_db, Prediction, TrainingRun
from config import MODEL_CACHE_FILE, MODEL_METADATA_FILE
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["predictions"])
limiter = Limiter(key_func=get_remote_address)

# ── Predictor singleton (shared, loaded from cache in main.py lifespan) ───────
_predictor = FootballPredictor()


def get_predictor() -> FootballPredictor:
    return _predictor


# ─── Schemas ──────────────────────────────────────────────────────────────────

# More permissive regex for international team names (allows & / ( ) , and more Unicode ranges)
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9 \-'\.\u00C0-\u024F&/(),]+$")

# ─── In-memory stores for Batch Predictions ──────────────────────────────────
_batch_store: Dict[str, Any] = {}
_prediction_store: Dict[str, Any] = {}


class PlayerSchema(BaseModel):
    player_id: Optional[str] = ""
    name: str = "Unknown"
    position: str = "CM"
    jersey_no: int = 0
    goals_season: int = 0
    xg_per90: float = 0.2
    recent_form_goals: int = 0
    penalty_taker: bool = False


class PredictRequest(BaseModel):
    home_team: str
    away_team: str
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    competition_code: str = "PL"
    home_lineup: List[PlayerSchema] = []
    away_lineup: List[PlayerSchema] = []
    home_subs: List[PlayerSchema] = []
    away_subs: List[PlayerSchema] = []
    home_position: int = 10
    away_position: int = 10
    match_importance: float = 1.0
    data_source: str = "api"
    csv_data: Optional[List[Dict]] = None
    match_date: Optional[str] = None
    venue: Optional[str] = None
    competition_name: Optional[str] = None

    @field_validator("home_team", "away_team")
    @classmethod
    def sanitize_team_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Team name must be 100 characters or fewer")
        if v and not _SAFE_NAME_RE.match(v):
            raise ValueError(
                "Team name may only contain letters, digits, spaces, hyphens, apostrophes and dots"
            )
        return v

    @field_validator("home_position", "away_position")
    @classmethod
    def validate_position(cls, v: int) -> int:
        if not 1 <= v <= 20:
            raise ValueError("League position must be between 1 and 20")
        return v

    @field_validator("match_importance")
    @classmethod
    def validate_importance(cls, v: float) -> float:
        if not 0.5 <= v <= 2.0:
            raise ValueError("match_importance must be between 0.5 and 2.0")
        return v

    @model_validator(mode="after")
    def validate_lineup_sizes(self) -> "PredictRequest":
        if len(self.home_lineup) > 11:
            raise ValueError("home_lineup must have at most 11 players")
        if len(self.away_lineup) > 11:
            raise ValueError("away_lineup must have at most 11 players")
        if len(self.home_subs) > 9:
            raise ValueError("home_subs must have at most 9 players")
        if len(self.away_subs) > 9:
            raise ValueError("away_subs must have at most 9 players")
        return self


class BatchPredictRequest(BaseModel):
    matches: List[PredictRequest]
    competition_code: Optional[str] = "PL"
    include_player_scorers: bool = False


class BatchPredictResponse(BaseModel):
    batch_id: str
    total: int
    successful: int
    failed: int
    results: List[Dict]
    generated_at: str


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/predict")
@limiter.limit("30/minute")
async def predict(
    request: Request,
    req: PredictRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run all 10 prediction models for a given match."""
    logger.info("Prediction request: %s vs %s", req.home_team, req.away_team)

    # ── Build historical DataFrame ──────────────────────────────────────────
    match_history = pd.DataFrame()

    if req.data_source == "csv" and req.csv_data:
        match_history = csv_parser.dataframe_from_records(req.csv_data)
    elif req.data_source == "api" and req.home_team_id and req.away_team_id:
        try:
            home_matches = await football_api.get_team_matches(req.home_team_id, limit=40)
            away_matches = await football_api.get_team_matches(req.away_team_id, limit=40)
            match_history = pd.DataFrame(home_matches + away_matches)
        except Exception as exc:
            logger.warning("Failed to fetch team matches: %s", exc)
            match_history = pd.DataFrame()

    # ── Train if needed ─────────────────────────────────────────────────────
    if not match_history.empty and not _predictor.is_trained:
        train_result = _predictor.train(match_history)
        if train_result.get("status") == "trained":
            _predictor.save_model()
            # Persist training run
            run = TrainingRun(
                samples=_predictor.training_samples,
                metrics_json=json.dumps(_predictor.metrics),
                model_path=MODEL_CACHE_FILE,
            )
            db.add(run)
            await db.commit()

    # ── Run predictions ─────────────────────────────────────────────────────
    home_lineup_dicts = [p.model_dump() for p in req.home_lineup]
    away_lineup_dicts = [p.model_dump() for p in req.away_lineup]

    results = _predictor.predict_all(
        home_team=req.home_team,
        away_team=req.away_team,
        match_history=match_history,
        home_position=req.home_position,
        away_position=req.away_position,
        match_importance=req.match_importance,
        home_lineup=home_lineup_dicts,
        away_lineup=away_lineup_dicts,
    )

    # ── Persist prediction to DB ────────────────────────────────────────────
    prediction_id = str(uuid.uuid4())
    payload = {
        "home_lineup": home_lineup_dicts,
        "away_lineup": away_lineup_dicts,
        "home_subs": [p.model_dump() for p in req.home_subs],
        "away_subs": [p.model_dump() for p in req.away_subs],
    }
    pred_row = Prediction(
        prediction_id=prediction_id,
        home_team=req.home_team,
        away_team=req.away_team,
        competition=req.competition_code,
        match_date=req.match_date or "",
        payload_json=json.dumps(payload),
        result_json=json.dumps(results, default=str),
        model_confidence=results.get("model_confidence"),
    )
    db.add(pred_row)
    await db.commit()
    logger.info("Prediction %s saved to DB", prediction_id)

    return {
        "prediction_id": prediction_id,
        "is_trained": _predictor.is_trained,
        "training_samples": _predictor.training_samples,
        **results,
    }


@router.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(
    req: BatchPredictRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run multiple predictions concurrently (semaphore 5 for stability)."""

    # 1. Fetch history for all unique competitions in the batch
    match_history = pd.DataFrame()
    unique_comps = list(set(m.competition_code for m in req.matches if m.competition_code))
    if not unique_comps:
        unique_comps = ["PL"]
    
    try:
        all_histories = []
        # Parallel fetch for all unique competitions to speed up multi-league batches
        fetch_tasks = [football_api.get_competition_matches(cc, status="FINISHED") for cc in unique_comps]
        all_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        for i, res in enumerate(all_results):
            comp_code = unique_comps[i]
            if isinstance(res, Exception):
                logger.warning("Failed to fetch history for %s: %s", comp_code, res)
            elif res:
                all_histories.extend(res)
                logger.info("Fetched %d historical matches for %s", len(res), comp_code)
        
        if all_histories:
            match_history = pd.DataFrame(all_histories)
            # Auto-train if we have enough and not trained
            if not _predictor.is_trained and len(match_history) > 30:
                logger.info("Auto-training model on %d historical matches...", len(match_history))
                _predictor.train(match_history)
    except Exception as exc:
        logger.error("Batch competition history fetch failed: %s", exc)

    batch_id = str(uuid.uuid4())
    semaphore = asyncio.Semaphore(5)

    async def run_single_predict(match_req: PredictRequest):
        async with semaphore:
            try:
                # Filter history for these specific teams using IDs for precision
                local_history = pd.DataFrame()
                if not match_history.empty:
                    # Standardize IDs to int for comparison
                    try:
                        hid = int(match_req.home_team_id) if match_req.home_team_id else -1
                        aid = int(match_req.away_team_id) if match_req.away_team_id else -1
                    except:
                        hid, aid = -1, -1

                    # Preference: ID filtering (most accurate)
                    local_history = match_history[
                        (match_history["home_team_id"] == hid) |
                        (match_history["away_team_id"] == hid) |
                        (match_history["home_team_id"] == aid) |
                        (match_history["away_team_id"] == aid) |
                        (match_history["home_team"].str.contains(match_req.home_team, case=False, na=False)) |
                        (match_history["away_team"].str.contains(match_req.home_team, case=False, na=False))
                    ]

                results = _predictor.predict_all(
                    home_team=match_req.home_team,
                    away_team=match_req.away_team,
                    match_history=local_history,
                    home_position=match_req.home_position,
                    away_position=match_req.away_position,
                    match_importance=match_req.match_importance,
                    home_lineup=[p.model_dump() for p in match_req.home_lineup],
                    away_lineup=[p.model_dump() for p in match_req.away_lineup],
                    home_team_id=match_req.home_team_id,
                    away_team_id=match_req.away_team_id,
                )
                pred_id = str(uuid.uuid4())
                res = {
                    "prediction_id": pred_id,
                    "home_team": match_req.home_team,
                    "away_team": match_req.away_team,
                    "match_date": match_req.match_date or "",
                    "competition_code": match_req.competition_code or "",
                    "competition_name": match_req.competition_name or "",
                    "success": True,
                    **results,
                }
                _prediction_store[pred_id] = res
                return res
            except Exception as e:
                logger.error("Batch item error: %s", e)
                return {
                    "home_team": match_req.home_team,
                    "away_team": match_req.away_team,
                    "match_date": match_req.match_date or "",
                    "competition_code": match_req.competition_code or "",
                    "competition_name": match_req.competition_name or "",
                    "success": False,
                    "error": str(e),
                }

    tasks = [run_single_predict(m) for m in req.matches]
    results = await asyncio.gather(*tasks)

    successful = [r for r in results if r.get("success")]
    response = BatchPredictResponse(
        batch_id=batch_id,
        total=len(req.matches),
        successful=len(successful),
        failed=len(req.matches) - len(successful),
        results=results,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    _batch_store[batch_id] = response.model_dump()
    return response


@router.get("/predict/batch/{batch_id}", response_model=BatchPredictResponse)
async def get_batch(batch_id: str):
    """Retrieve previously computed batch results."""
    if batch_id not in _batch_store:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_store[batch_id]


@router.get("/export/batch/{batch_id}")
async def export_batch(
    batch_id: str,
    min_prob: float = Query(0.0, alias="min_prob"),
    market: str = Query("any", alias="market")
):
    """
    Export whole batch results as a multi-sheet Excel file.
    Supports filtering by min_prob (0.0-1.0) and market type.
    """
    logger.debug("Export batch request - ID: %s, MinProb: %s, Market: %s", batch_id, min_prob, market)
    
    if batch_id not in _batch_store:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch_data = _batch_store[batch_id]
    all_results = batch_data["results"]
    
    # ── Filtering Logic ───────────────────────────────────────────────────────
    results = all_results
    if min_prob > 0 or market != "any":
        filtered = []
        for r in all_results:
            if not r.get("success"):
                continue
            
            # Safe extraction: prediction data might be on root or in "result" key
            p = r.get("result", r)
            mr = p.get("match_result", {})
            dc = p.get("double_chance", {})
            btts = p.get("btts", {})
            ou = p.get("total_goals", {}).get("over_under", {}) if isinstance(p.get("total_goals"), dict) else {}
            
            match = False
            if market == "any":
                # Check if ANY of the main markets meets the threshold
                vals = [
                    mr.get("home", 0), mr.get("draw", 0), mr.get("away", 0),
                    dc.get("1X", 0), dc.get("12", 0), dc.get("X2", 0),
                    btts.get("yes", 0), ou.get("over_2_5", 0)
                ]
                if any(v is not None and v >= min_prob for v in vals):
                    match = True
            elif market == "home":
                if mr.get("home", 0) >= min_prob: match = True
            elif market == "draw":
                if mr.get("draw", 0) >= min_prob: match = True
            elif market == "away":
                if mr.get("away", 0) >= min_prob: match = True
            elif market == "double_chance":
                if any(dc.get(k, 0) >= min_prob for k in ["1X", "12", "X2"]):
                    match = True
            elif market == "btts":
                if btts.get("yes", 0) >= min_prob: match = True
            elif market == "over25":
                if ou.get("over_2_5", 0) >= min_prob: match = True
            
            if match:
                filtered.append(r)
        
        logger.info("Batch filter: %d matches kept out of %d (Market: %s, Threshold: %.2f)", 
                    len(filtered), len(all_results), market, min_prob)
        results = filtered

    if not results:
        msg = f"No matches found matching criteria (Market: {market}, Min Prob: {min_prob*100:.0f}%)"
        raise HTTPException(status_code=400, detail=msg)

    try:
        filter_ctx = {
            "market": market,
            "min_prob": min_prob,
            "count": len(results)
        }
        xlsx_bytes = excel_exporter.export_batch(results, filters=filter_ctx)
    except Exception as exc:
        logger.error("Batch export failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Batch export failed: {exc}")

    filename = f"batch_prediction_{batch_id[:8]}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/train")
async def train_model(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Train the prediction model from uploaded CSV data."""
    records = data.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No training data provided")

    df = pd.DataFrame(records)
    result = _predictor.train(df)

    if result.get("status") == "trained":
        _predictor.save_model()
        run = TrainingRun(
            samples=_predictor.training_samples,
            metrics_json=json.dumps(_predictor.metrics),
            model_path=MODEL_CACHE_FILE,
        )
        db.add(run)
        await db.commit()

    return result


@router.get("/export/{prediction_id}")
async def export_prediction(
    prediction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Export prediction results as Excel .xlsx file."""
    result = await db.execute(
        select(Prediction).where(Prediction.prediction_id == prediction_id)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    results_data = json.loads(pred.result_json)
    payload_data = json.loads(pred.payload_json) if pred.payload_json else {}
    match_info = {
        "home_team": pred.home_team,
        "away_team": pred.away_team,
        "competition": pred.competition,
        "date": pred.match_date,
        "home_lineup": payload_data.get("home_lineup", []),
        "away_lineup": payload_data.get("away_lineup", []),
    }

    try:
        xlsx_bytes = excel_exporter.export(results_data, match_info)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}")

    home = pred.home_team.replace(" ", "_")
    away = pred.away_team.replace(" ", "_")
    filename = f"prediction_{home}_vs_{away}.xlsx"

    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/model/status")
async def model_status():
    return {
        "is_trained": _predictor.is_trained,
        "training_samples": _predictor.training_samples,
    }


@router.get("/model/info")
async def model_info():
    """Return model metadata (trained_at, samples, version, metrics)."""
    meta_path = Path(MODEL_METADATA_FILE)
    if not meta_path.exists():
        return {
            "is_trained": _predictor.is_trained,
            "training_samples": _predictor.training_samples,
            "message": "No persisted model found",
        }
    with open(meta_path) as f:
        return json.load(f)


@router.get("/model/metrics")
async def model_metrics():
    """Return backtesting metrics from the last training run."""
    if not _predictor.is_trained:
        raise HTTPException(status_code=404, detail="Model not yet trained")
    return {
        "metrics": _predictor.metrics,
        "training_samples": _predictor.training_samples,
    }


@router.delete("/model/cache")
async def delete_model_cache():
    """Delete cached model files and reset predictor to untrained state."""
    global _predictor
    for path in [MODEL_CACHE_FILE, MODEL_METADATA_FILE]:
        p = Path(path)
        if p.exists():
            p.unlink()
            logger.info("Deleted model cache: %s", path)
    _predictor = FootballPredictor()
    return {"status": "cache_cleared", "message": "Model reset. Retrain on next prediction."}


@router.get("/predictions/history")
async def prediction_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Return last N predictions from the database."""
    result = await db.execute(
        select(Prediction)
        .order_by(Prediction.created_at.desc())
        .limit(min(limit, 100))
    )
    rows = result.scalars().all()
    return {"predictions": [r.to_dict() for r in rows], "count": len(rows)}


@router.delete("/predictions/history")
async def clear_history(db: AsyncSession = Depends(get_db)):
    """Clear all prediction history from the database."""
    await db.execute(delete(Prediction))
    await db.commit()
    return {"status": "cleared"}


@router.post("/train/competition/{code}")
async def train_competition(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Seed the model with historical data from an entire competition."""
    try:
        if _predictor.is_trained:
            return {"status": "already_trained", "samples": _predictor.training_samples}

        logger.info("Fetching season history for %s...", code)
        matches = await football_api.get_competition_matches(code, status="FINISHED")
        if not matches:
            return {"status": "no_data_found", "code": code}

        df = pd.DataFrame(matches)
        result = _predictor.train(df)

        if result.get("status") == "trained":
            _predictor.save_model()
            run = TrainingRun(
                samples=_predictor.training_samples,
                metrics_json=json.dumps(_predictor.metrics),
                model_path=MODEL_CACHE_FILE,
            )
            db.add(run)
            await db.commit()

        return result
    except Exception as exc:
        logger.error("Competition training failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
