import io
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


# Column mapping: football-data.co.uk → internal names
COLUMN_MAP = {
    "Div": "division",
    "Date": "date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "home_goals",
    "FTAG": "away_goals",
    "FTR": "full_time_result",
    "HTHG": "home_ht_goals",
    "HTAG": "away_ht_goals",
    "HTR": "half_time_result",
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellows",
    "AY": "away_yellows",
    "HR": "home_reds",
    "AR": "away_reds",
    "B365H": "b365_home_odds",
    "B365D": "b365_draw_odds",
    "B365A": "b365_away_odds",
    "BbAvH": "bb_avg_home_odds",
    "BbAvD": "bb_avg_draw_odds",
    "BbAvA": "bb_avg_away_odds",
    "PSCH": "ps_home_odds",
    "PSCD": "ps_draw_odds",
    "PSCA": "ps_away_odds",
}

REQUIRED_COLUMNS = ["home_team", "away_team", "home_goals", "away_goals"]


class CSVParser:
    """
    Parses CSV files from football-data.co.uk.
    Maps columns gracefully if some are missing.
    Handles various date formats.
    """

    def parse_file(self, file_content: bytes, filename: str = "") -> Dict[str, Any]:
        """
        Parse a CSV file. Returns:
          - data: list of match dicts
          - columns_found: list of recognized column names
          - columns_missing: list of expected but missing columns
          - warnings: list of warning messages
          - error: error message if parsing failed
        """
        try:
            df = self._read_csv(file_content)
        except Exception as e:
            return {"error": f"Failed to read CSV: {str(e)}", "data": [], "columns_found": [], "columns_missing": []}

        # Rename known columns
        df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

        detected = list(df.columns)
        internal_cols = list(COLUMN_MAP.values())
        columns_found = [c for c in detected if c in internal_cols]
        columns_missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

        warnings = []
        if columns_missing:
            warnings.append(f"Missing required columns: {columns_missing}")
            if "home_goals" not in df.columns:
                df["home_goals"] = 0
            if "away_goals" not in df.columns:
                df["away_goals"] = 0
            if "home_team" not in df.columns or "away_team" not in df.columns:
                return {
                    "error": "CSV missing HomeTeam/AwayTeam columns — cannot parse",
                    "data": [], "columns_found": columns_found, "columns_missing": columns_missing,
                }

        # Parse date
        df = self._parse_date(df, warnings)

        # Clean numeric columns
        numeric_cols = [
            "home_goals", "away_goals", "home_ht_goals", "away_ht_goals",
            "home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target",
            "home_fouls", "away_fouls", "home_corners", "away_corners",
            "home_yellows", "away_yellows", "home_reds", "away_reds",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Drop rows with no team names
        df = df.dropna(subset=["home_team", "away_team"])
        df = df[df["home_team"].astype(str).str.strip() != ""]

        # Add match_importance column (default 1.0)
        df["match_importance"] = 1.0

        records = df.to_dict(orient="records")
        # Convert any remaining NaN to None for JSON compatibility
        clean_records = [
            {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()}
            for r in records
        ]

        return {
            "data": clean_records,
            "columns_found": columns_found,
            "columns_missing": columns_missing,
            "warnings": warnings,
            "rows": len(clean_records),
            "column_preview": self._build_column_preview(df),
        }

    def _read_csv(self, file_content: bytes) -> pd.DataFrame:
        """Try different encodings to read CSV."""
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                return pd.read_csv(io.BytesIO(file_content), encoding=encoding, low_memory=False)
            except UnicodeDecodeError:
                continue
        raise ValueError("Unable to decode CSV with common encodings")

    @staticmethod
    def _parse_date(df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
        if "date" not in df.columns:
            warnings.append("No date column found")
            df["date"] = pd.NaT
            return df
        formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y"]
        for fmt in formats:
            try:
                df["date"] = pd.to_datetime(df["date"], format=fmt, errors="coerce")
                valid = df["date"].notna().sum()
                if valid > len(df) * 0.5:
                    return df
            except Exception:
                continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce", infer_datetime_format=True)
        return df

    @staticmethod
    def _build_column_preview(df: pd.DataFrame) -> List[Dict]:
        """Build column info for frontend preview table."""
        preview = []
        for col in df.columns[:20]:  # Limit to 20 cols for UI
            sample = df[col].dropna().head(3).tolist()
            preview.append({
                "name": col,
                "type": str(df[col].dtype),
                "sample": [str(s) for s in sample],
                "null_count": int(df[col].isna().sum()),
            })
        return preview

    def dataframe_from_records(self, records: List[Dict]) -> pd.DataFrame:
        """Convert list of match dicts back to DataFrame for ML."""
        return pd.DataFrame(records)


# Singleton
csv_parser = CSVParser()
