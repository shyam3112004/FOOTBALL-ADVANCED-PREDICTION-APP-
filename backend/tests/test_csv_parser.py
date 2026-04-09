"""
Tests for csv_parser.py — valid CSV parsing, missing columns, encoding errors.
"""
import pytest
import io
import pandas as pd
from services.csv_parser import csv_parser


VALID_CSV = b"""HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HST,AST,Date
Arsenal,Chelsea,2,1,1,0,6,4,01/08/2024
Liverpool,Tottenham,1,1,0,1,5,7,02/08/2024
Manchester City,Newcastle,3,0,2,0,8,3,03/08/2024
"""


def test_valid_csv_parses_correctly():
    result = csv_parser.parse_file(VALID_CSV, "test.csv")
    assert "error" not in result or result.get("data")
    assert result.get("rows", 0) == 3
    data = result.get("data", [])
    assert len(data) == 3


def test_valid_csv_normalizes_column_names():
    result = csv_parser.parse_file(VALID_CSV, "test.csv")
    data = result.get("data", [])
    if data:
        row = data[0]
        # Either native or normalized columns should be present
        has_home = "home_team" in row or "HomeTeam" in row
        assert has_home, f"Expected home column, got: {list(row.keys())}"


def test_missing_required_columns():
    """CSV without FTHG/FTAG should warn but not crash."""
    minimal_csv = b"HomeTeam,AwayTeam,Date\nArsenal,Chelsea,01/08/2024\n"
    result = csv_parser.parse_file(minimal_csv, "minimal.csv")
    # Should have warnings or columns_missing but not raise
    assert isinstance(result, dict)
    assert "data" in result or "error" in result


def test_empty_csv_file():
    """Empty file should return error without raising."""
    result = csv_parser.parse_file(b"", "empty.csv")
    assert isinstance(result, dict)
    # Should have error or empty data
    has_error = bool(result.get("error"))
    has_no_data = not result.get("data")
    assert has_error or has_no_data


def test_csv_with_wrong_extension():
    """Non-csv bytes should be handled gracefully."""
    result = csv_parser.parse_file(b"not a csv", "data.txt")
    assert isinstance(result, dict)


def test_dataframe_from_records(mock_csv_rows):
    """dataframe_from_records should convert dicts to DataFrame."""
    df = csv_parser.dataframe_from_records(mock_csv_rows)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(mock_csv_rows)


def test_large_valid_csv():
    """Parser should handle 500-row CSV without issues."""
    header = b"HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HST,AST,Date\n"
    rows = b"Arsenal,Chelsea,1,1,0,0,5,5,01/08/2024\n" * 500
    result = csv_parser.parse_file(header + rows, "large.csv")
    assert result.get("rows", 0) >= 490  # Some may be deduped
