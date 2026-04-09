"""
Tests for FootballFeatureEngineer — feature extraction and training data build.
"""
import pytest
import pandas as pd
import numpy as np
from models.feature_engineering import FootballFeatureEngineer


@pytest.fixture
def engineer():
    return FootballFeatureEngineer()


def test_build_match_features_returns_dict(engineer, sample_match_df):
    features = engineer.build_match_features(
        "Arsenal", "Chelsea", sample_match_df
    )
    assert isinstance(features, dict)
    assert len(features) > 0


def test_build_match_features_all_numeric(engineer, sample_match_df):
    features = engineer.build_match_features(
        "Arsenal", "Chelsea", sample_match_df
    )
    for k, v in features.items():
        assert isinstance(v, (int, float)), f"{k} is not numeric: {v}"


def test_build_match_features_expected_keys(engineer, sample_match_df):
    features = engineer.build_match_features(
        "Arsenal", "Chelsea", sample_match_df
    )
    required = [
        "home_avg_goals_scored_5",
        "away_avg_goals_scored_5",
        "home_win_rate_10",
        "away_win_rate_10",
        "home_form_points",
        "away_form_points",
        "match_importance_weight",
    ]
    for key in required:
        assert key in features, f"Missing feature: {key}"


def test_build_match_features_no_data(engineer):
    """Feature builder should return default values when no history available."""
    features = engineer.build_match_features(
        "Team A", "Team B", pd.DataFrame()
    )
    assert isinstance(features, dict)
    # Defaults should be reasonable
    assert 0.5 <= features["home_avg_goals_scored_5"] <= 3.0


def test_build_training_data_returns_rows(engineer, sample_match_df):
    training_df = engineer.build_training_data(sample_match_df)
    # Should remove first 20 rows for warmup
    assert len(training_df) > 0
    assert len(training_df) <= len(sample_match_df)


def test_build_training_data_columns(engineer, sample_match_df):
    training_df = engineer.build_training_data(sample_match_df)
    # Must contain target columns
    targets = ["target_home_goals", "target_away_goals", "target_home_win",
               "target_btts", "target_both_halves"]
    for t in targets:
        assert t in training_df.columns, f"Missing target: {t}"


def test_build_training_data_no_nulls_in_targets(engineer, sample_match_df):
    training_df = engineer.build_training_data(sample_match_df)
    for col in ["target_home_goals", "target_away_goals"]:
        if col in training_df.columns:
            assert training_df[col].isnull().sum() == 0, f"Nulls in {col}"


def test_features_to_array_correct_shape(engineer, sample_match_df):
    features = engineer.build_match_features("Arsenal", "Chelsea", sample_match_df)
    arr = engineer.features_to_array(features)
    assert arr.shape == (1, len(features))


def test_get_feature_names_consistent(engineer):
    """Feature names list must be stable across calls."""
    names1 = engineer.get_feature_names()
    names2 = engineer.get_feature_names()
    assert names1 == names2
    assert len(names1) > 20  # Should have meaningful number of features


def test_build_training_data_insufficient(engineer):
    """Fewer than 20 rows should return empty DataFrame."""
    tiny_df = pd.DataFrame([
        {"date": "2024-01-01", "home_team": "A", "away_team": "B",
         "home_goals": 1, "away_goals": 0}
    ] * 5)
    result = engineer.build_training_data(tiny_df)
    assert len(result) == 0
