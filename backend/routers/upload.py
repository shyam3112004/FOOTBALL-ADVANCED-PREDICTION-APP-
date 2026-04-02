from fastapi import APIRouter, UploadFile, File, HTTPException
from services.csv_parser import csv_parser
from routers.predictions import _predictor
import pandas as pd

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Accept a CSV file from football-data.co.uk.
    Returns parsed data with column preview before full processing.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

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
        "sample": result.get("data", [])[:5],  # First 5 rows for preview
    }


@router.post("/upload-csv/train")
async def upload_and_train(file: UploadFile = File(...)):
    """Upload CSV and immediately train the prediction model."""
    content = await file.read()
    result = csv_parser.parse_file(content, file.filename)

    if not result.get("data"):
        raise HTTPException(status_code=422, detail=result.get("error", "No data parsed"))

    df = pd.DataFrame(result["data"])
    train_result = _predictor.train(df)

    return {
        "upload": {
            "rows": result.get("rows", 0),
            "columns_found": result.get("columns_found", []),
            "warnings": result.get("warnings", []),
        },
        "training": train_result,
    }
