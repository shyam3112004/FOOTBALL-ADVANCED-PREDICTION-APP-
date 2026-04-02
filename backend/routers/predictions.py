import uuid
from typing import Dict, List, Optional, Any
import pandas as pd

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from models.linear_regression import FootballPredictor
from services.football_api import football_api
from services.csv_parser import csv_parser
from services.excel_exporter import excel_exporter

router = APIRouter(prefix="/api", tags=["predictions"])

# In-memory store for predictions (keyed by prediction_id)
_prediction_store: Dict[str, Dict] = {}
_predictor = FootballPredictor()


# ─── Schemas ─────────────────────────────────────────────────────────────────

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
    data_source: str = "api"  # "api" | "csv"
    csv_data: Optional[List[Dict]] = None
    match_date: Optional[str] = None
    venue: Optional[str] = None


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/predict")
async def predict(req: PredictRequest):
    """Run all 10 prediction models for a given match."""

    # ── Build historical DataFrame ────────────────────────────────────────────
    match_history = pd.DataFrame()

    if req.data_source == "csv" and req.csv_data:
        match_history = csv_parser.dataframe_from_records(req.csv_data)
    elif req.data_source == "api" and req.home_team_id and req.away_team_id:
        try:
            home_matches = await football_api.get_team_matches(req.home_team_id, limit=40)
            away_matches = await football_api.get_team_matches(req.away_team_id, limit=40)
            combined = home_matches + away_matches
            match_history = pd.DataFrame(combined)
        except Exception as e:
            match_history = pd.DataFrame()

    # ── Train predictor if enough data ───────────────────────────────────────
    if not match_history.empty and not _predictor.is_trained:
        _predictor.train(match_history)

    # ── Run predictions ───────────────────────────────────────────────────────
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

    # ── Store prediction ──────────────────────────────────────────────────────
    prediction_id = str(uuid.uuid4())
    _prediction_store[prediction_id] = {
        "results": results,
        "match_info": {
            "home_team": req.home_team,
            "away_team": req.away_team,
            "competition": req.competition_code,
            "date": req.match_date or "",
            "venue": req.venue or "",
            "home_lineup": home_lineup_dicts,
            "away_lineup": away_lineup_dicts,
            "home_subs": [p.model_dump() for p in req.home_subs],
            "away_subs": [p.model_dump() for p in req.away_subs],
        },
    }

    return {
        "prediction_id": prediction_id,
        "is_trained": _predictor.is_trained,
        "training_samples": _predictor.training_samples,
        **results,
    }


@router.post("/train")
async def train_model(data: Dict[str, Any]):
    """Train the prediction model from uploaded CSV data."""
    records = data.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No training data provided")

    df = pd.DataFrame(records)
    result = _predictor.train(df)
    return result


@router.get("/export/{prediction_id}")
async def export_prediction(prediction_id: str):
    """Export prediction results as Excel .xlsx file."""
    if prediction_id not in _prediction_store:
        raise HTTPException(status_code=404, detail="Prediction not found")

    stored = _prediction_store[prediction_id]
    try:
        xlsx_bytes = excel_exporter.export(stored["results"], stored["match_info"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    home = stored["match_info"].get("home_team", "Home").replace(" ", "_")
    away = stored["match_info"].get("away_team", "Away").replace(" ", "_")
    filename = f"prediction_{home}_vs_{away}.xlsx"

    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/model/status")
async def model_status():
    """Get current model training status."""
    return {
        "is_trained": _predictor.is_trained,
        "training_samples": _predictor.training_samples,
    }


@router.post("/train/competition/{code}")
async def train_competition(code: str):
    """Seed the model with historical data from an entire competition."""
    try:
        # Fetch status for response
        if _predictor.is_trained:
             return {"status": "already_trained", "samples": _predictor.training_samples}

        msg = f"Fetching season history for {code}..."
        print(msg)
        
        # Get matches for current season (all completed ones)
        matches = await football_api.get_competition_matches(code, status="FINISHED")
        if not matches:
             return {"status": "no_data_found", "code": code}

        df = pd.DataFrame(matches)
        result = _predictor.train(df)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
