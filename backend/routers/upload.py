from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.csv_parser import csv_parser
from routers.predictions import _predictor
from logger import get_logger
import pandas as pd

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/upload-csv")
@limiter.limit("5/minute")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Accept a CSV file from football-data.co.uk.
    Returns parsed data with column preview before full processing.
    Rate-limited to 5 uploads/minute per IP.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    logger.info("CSV upload: %s (%d bytes)", file.filename, len(content))
    result = csv_parser.parse_file(content, file.filename)

    if "error" in result and not result.get("data"):
        raise HTTPException(status_code=422, detail=result["error"])

    return {
        "filename": file.filename,
        "rows": result.get("rows", 0),
        "columns_found": result.get("columns_found", []),
        "columns_missing": result.get("columns_missing", []),
        "warnings": result.get("warnings", []),
        "column_preview": result.get("column_preview", []),
        "data": result.get("data", []),
        "sample": result.get("data", [])[:5],
    }


@router.post("/upload-csv/train")
@limiter.limit("5/minute")
async def upload_and_train(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload CSV and immediately train the prediction model."""
    content = await file.read()
    result = csv_parser.parse_file(content, file.filename)

    if not result.get("data"):
        raise HTTPException(status_code=422, detail=result.get("error", "No data parsed"))

    logger.info(
        "Training from CSV: %s rows=%d", file.filename, result.get("rows", 0)
    )
    df = pd.DataFrame(result["data"])
    train_result = _predictor.train(df)

    if train_result.get("status") == "trained":
        _predictor.save_model()

    return {
        "upload": {
            "rows": result.get("rows", 0),
            "columns_found": result.get("columns_found", []),
            "warnings": result.get("warnings", []),
        },
        "training": train_result,
    }
