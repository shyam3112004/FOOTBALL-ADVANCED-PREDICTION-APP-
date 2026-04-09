"""
Tests for the /api/predict endpoint and FootballPredictor.predict_all().
"""
import pytest
from models.linear_regression import FootballPredictor
import pandas as pd


# ── Unit: predict_all structure ────────────────────────────────────────────────

def test_predict_all_untrained_contains_all_keys(sample_match_df):
    """Untrained model (heuristic fallback) still returns all 10 categories."""
    predictor = FootballPredictor()
    result = predictor.predict_all(
        home_team="Arsenal", away_team="Chelsea",
        match_history=pd.DataFrame(),
    )
    required_keys = [
        "match_result", "double_chance", "btts", "total_goals",
        "correct_scores", "score_draw", "total_even_odd",
        "goal_both_halves", "goal_interval", "player_scorers",
        "model_confidence",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


def test_match_result_probabilities_sum_to_one(sample_match_df):
    """1X2 probabilities must sum to ≈1."""
    predictor = FootballPredictor()
    result = predictor.predict_all("Arsenal", "Chelsea", sample_match_df)
    mr = result["match_result"]
    total = mr["home"] + mr["draw"] + mr["away"]
    assert abs(total - 1.0) < 0.02, f"Probs sum to {total}"


def test_btts_probabilities_sum_to_one(sample_match_df):
    predictor = FootballPredictor()
    result = predictor.predict_all("Arsenal", "Chelsea", sample_match_df)
    btts = result["btts"]
    assert abs(btts["yes"] + btts["no"] - 1.0) < 0.02


def test_correct_scores_sorted_by_probability(sample_match_df):
    predictor = FootballPredictor()
    result = predictor.predict_all("Arsenal", "Chelsea", sample_match_df)
    cs = result["correct_scores"]
    probs = [s["probability"] for s in cs]
    assert probs == sorted(probs, reverse=True)


def test_trained_predictor_metrics_populated(trained_predictor):
    """After training, predictor.metrics must contain key accuracy fields."""
    metrics = trained_predictor.metrics
    assert "home_win_accuracy" in metrics
    assert 0.0 <= metrics["home_win_accuracy"] <= 1.0


def test_goal_interval_probabilities_sum_to_one(trained_predictor, sample_match_df):
    result = trained_predictor.predict_all("Arsenal", "Chelsea", sample_match_df)
    gi = result["goal_interval"]
    total = sum(gi.values())
    assert abs(total - 1.0) < 0.05


def test_predict_with_lineup(trained_predictor, sample_match_df):
    """Player scorers are generated when lineup is provided."""
    lineup = [{"name": "Saka", "position": "RW", "xg_per90": 0.4, "goals_season": 16}]
    result = trained_predictor.predict_all(
        "Arsenal", "Chelsea", sample_match_df,
        home_lineup=lineup,
    )
    scorers = result["player_scorers"]
    assert len(scorers) >= 1
    assert scorers[0]["name"] == "Saka"


def test_save_and_load_model(trained_predictor, tmp_path):
    """Model saves and reloads preserving is_trained and training_samples."""
    save_path = str(tmp_path / "test_model.joblib")
    trained_predictor.save_model(save_path)

    loaded = FootballPredictor.load_model(save_path)
    assert loaded.is_trained
    assert loaded.training_samples == trained_predictor.training_samples
