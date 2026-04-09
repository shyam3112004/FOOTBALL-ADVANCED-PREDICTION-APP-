import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.metrics import (
    accuracy_score, mean_absolute_error, brier_score_loss
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

from models.feature_engineering import FootballFeatureEngineer
from config import MAX_CORRECT_SCORE, MIN_MATCHES_FOR_TRAINING, MODEL_CACHE_FILE, MODEL_METADATA_FILE, MODEL_CACHE_DIR
from logger import get_logger

logger = get_logger(__name__)


class FootballPredictor:
    """
    Wraps all 10 XGBoost prediction models for football match outcomes.
    Trains on historical match data and predicts probabilities for upcoming fixtures.

    Interface is identical to the original LinearRegression version so
    nothing else in the codebase changes.
    """

    # XGBoost hyperparameter defaults (sensible out-of-the-box)
    XGB_PARAMS = dict(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
        eval_metric="logloss",
    )

    def __init__(self):
        self.feature_engineer = FootballFeatureEngineer()
        self.is_trained = False
        self.training_samples = 0
        self.metrics: Dict[str, float] = {}

        self._models: Dict[str, Any] = {}
        self._init_models()

    # ─────────────────────────────────────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────────────────────────────────────

    def _init_models(self):
        """Initialize all model pipelines with XGBoost estimators."""

        def clf_pipeline():
            return Pipeline([
                ("scaler", StandardScaler()),
                ("model", XGBClassifier(**self.XGB_PARAMS)),
            ])

        def reg_pipeline():
            return Pipeline([
                ("scaler", StandardScaler()),
                ("model", XGBRegressor(**{k: v for k, v in self.XGB_PARAMS.items() if k != "eval_metric"})),
            ])

        def multi_reg_pipeline():
            return Pipeline([
                ("scaler", StandardScaler()),
                ("model", MultiOutputRegressor(
                    XGBRegressor(**{k: v for k, v in self.XGB_PARAMS.items() if k != "eval_metric"})
                )),
            ])

        self._models = {
            "home_win":     clf_pipeline(),
            "draw":         clf_pipeline(),
            "away_win":     clf_pipeline(),
            "btts":         clf_pipeline(),
            "both_halves":  clf_pipeline(),
            "goals_multi":  multi_reg_pipeline(),   # [total, home, away]
            "goal_intervals": multi_reg_pipeline(), # 7 intervals
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Training
    # ─────────────────────────────────────────────────────────────────────────────

    def train(self, match_history: pd.DataFrame) -> Dict[str, Any]:
        """Train all models from historical match data.  Returns metrics dict."""
        logger.info("Starting model training on %d raw rows", len(match_history))
        training_df = self.feature_engineer.build_training_data(match_history)

        if len(training_df) < MIN_MATCHES_FOR_TRAINING:
            logger.warning(
                "Insufficient training data: %d rows (need %d)",
                len(training_df), MIN_MATCHES_FOR_TRAINING
            )
            return {
                "status": "insufficient_data",
                "samples": len(training_df),
                "required": MIN_MATCHES_FOR_TRAINING,
            }

        feature_cols = self.feature_engineer.get_feature_names()
        feature_cols = [c for c in feature_cols if c in training_df.columns]

        # ── Train / test split (last 20% as hold-out) ─────────────────────────
        split_idx = int(len(training_df) * 0.8)
        train_df = training_df.iloc[:split_idx]
        test_df = training_df.iloc[split_idx:]

        X_train = train_df[feature_cols].fillna(0).values
        X_test = test_df[feature_cols].fillna(0).values
        self.training_samples = len(train_df)

        # ── Binary classifiers ────────────────────────────────────────────────
        for target, model_key in [
            ("target_home_win",  "home_win"),
            ("target_draw",      "draw"),
            ("target_away_win",  "away_win"),
            ("target_btts",      "btts"),
            ("target_both_halves", "both_halves"),
        ]:
            if target in train_df.columns:
                y_train = train_df[target].fillna(0.5).values.astype(int)
                self._models[model_key].fit(X_train, y_train)

        # ── Goals multi-output regressor ──────────────────────────────────────
        goal_targets = ["target_home_goals", "target_away_goals"]
        if all(c in train_df.columns for c in goal_targets):
            y_goals = train_df[goal_targets].fillna(1.2).values
            total = y_goals[:, 0] + y_goals[:, 1]
            y_goals_full = np.column_stack([total, y_goals[:, 0], y_goals[:, 1]])
            self._models["goals_multi"].fit(X_train, y_goals_full)

        # ── Goal intervals ────────────────────────────────────────────────────
        if "target_first_half_goals" in train_df.columns:
            y_intervals = self._synthesize_intervals(train_df)
            self._models["goal_intervals"].fit(X_train, y_intervals)

        self.is_trained = True

        # ── Backtesting metrics ───────────────────────────────────────────────
        self.metrics = self._compute_metrics(X_test, test_df, feature_cols)
        logger.info("Model trained. Samples=%d Metrics=%s", self.training_samples, self.metrics)

        return {
            "status": "trained",
            "samples": self.training_samples,
            "metrics": self.metrics,
        }

    def _compute_metrics(
        self, X_test: np.ndarray, test_df: pd.DataFrame, feature_cols: List[str]
    ) -> Dict[str, float]:
        """Compute backtesting metrics on the held-out test set."""
        metrics: Dict[str, float] = {}

        if len(test_df) == 0 or X_test.shape[0] == 0:
            return metrics

        try:
            # 1x2 accuracy
            for target, model_key, metric_key in [
                ("target_home_win", "home_win", "home_win_accuracy"),
                ("target_draw",     "draw",     "draw_accuracy"),
                ("target_away_win", "away_win", "away_win_accuracy"),
                ("target_btts",     "btts",     "btts_accuracy"),
            ]:
                if target in test_df.columns:
                    y_true = test_df[target].fillna(0).values.astype(int)
                    y_pred = self._models[model_key].predict(X_test)
                    metrics[metric_key] = round(float(accuracy_score(y_true, y_pred)), 4)
                    # Brier score on home_win as proxy for calibration
                    if metric_key == "home_win_accuracy":
                        try:
                            y_prob = self._models[model_key].predict_proba(X_test)[:, 1]
                            metrics["brier_score"] = round(float(brier_score_loss(y_true, y_prob)), 4)
                        except Exception:
                            pass

            # Goals MAE
            goal_targets = ["target_home_goals", "target_away_goals"]
            if all(c in test_df.columns for c in goal_targets):
                y_goals = test_df[goal_targets].fillna(1.2).values
                total_true = y_goals[:, 0] + y_goals[:, 1]
                raw = self._models["goals_multi"].predict(X_test)
                total_pred = np.clip(raw[:, 0], 0, 10)
                metrics["goals_mae"] = round(float(mean_absolute_error(total_true, total_pred)), 4)

        except Exception as exc:
            logger.warning("Metrics computation failed: %s", exc)

        return metrics

    def _synthesize_intervals(self, df: pd.DataFrame) -> np.ndarray:
        """Approximate interval probabilities from halftime goal data."""
        n = len(df)
        prior = np.array([0.12, 0.15, 0.13, 0.14, 0.16, 0.20, 0.10])
        y = np.tile(prior, (n, 1))
        if "target_first_half_goals" in df.columns:
            fhg = df["target_first_half_goals"].fillna(0).clip(0, 5)
            total = (df.get("target_home_goals", pd.Series(1.2, index=df.index)) +
                     df.get("target_away_goals", pd.Series(1.2, index=df.index))).fillna(2.4)
            fh_ratio = (fhg / total.replace(0, 2.4)).clip(0, 1)
            for i in range(3):
                y[:, i] = y[:, i] * (fh_ratio * 2)
            row_sums = y.sum(axis=1, keepdims=True)
            y = y / np.where(row_sums == 0, 1, row_sums)
        return y

    # ─────────────────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────────────────

    def save_model(self, path: Optional[str] = None) -> str:
        """Save trained predictor to disk. Returns the path written."""
        save_path = path or MODEL_CACHE_FILE
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, save_path)

        # Write metadata sidecar
        metadata = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "samples": self.training_samples,
            "version": "1.0",
            "metrics": self.metrics,
        }
        meta_path = path.replace(".joblib", "_metadata.json") if path else MODEL_METADATA_FILE
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Model saved to %s", save_path)
        return save_path

    @classmethod
    def load_model(cls, path: Optional[str] = None) -> "FootballPredictor":
        """Load a persisted predictor from disk."""
        load_path = path or MODEL_CACHE_FILE
        predictor: FootballPredictor = joblib.load(load_path)
        logger.info("Model loaded from %s (samples=%d)", load_path, predictor.training_samples)
        return predictor

    # ─────────────────────────────────────────────────────────────────────────────
    # Prediction (all 10 categories) — interface unchanged
    # ─────────────────────────────────────────────────────────────────────────────

    def predict_all(
        self,
        home_team: str,
        away_team: str,
        match_history: pd.DataFrame,
        home_position: int = 10,
        away_position: int = 10,
        match_importance: float = 1.0,
        home_lineup: Optional[List[Dict]] = None,
        away_lineup: Optional[List[Dict]] = None,
        home_team_id: Optional[int] = None,
        away_team_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run all 10 predictions for a given match."""
        features = self.feature_engineer.build_match_features(
            home_team, away_team, match_history,
            home_position, away_position, match_importance,
            home_lineup, away_lineup,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        X = self.feature_engineer.features_to_array(features)

        if not self.is_trained:
            return self._fallback_predictions(features, home_lineup, away_lineup)

        results = {}

        # 1. 1X2
        results["match_result"] = self._predict_1x2(X)
        # 2. Double Chance
        results["double_chance"] = self._predict_double_chance(results["match_result"])
        # 3. BTTS
        results["btts"] = self._predict_btts(X)
        # 4. Total Goals
        goals_pred = self._predict_goals(X, features)
        results["total_goals"] = goals_pred
        # 5. Correct Score (Poisson — unchanged)
        cs = self._predict_correct_scores(
            goals_pred["home_predicted"], goals_pred["away_predicted"]
        )
        results["correct_scores"] = cs
        # 6. Score Draw
        results["score_draw"] = self._predict_score_draw(cs)
        # 7. Even/Odd
        results["total_even_odd"] = self._predict_even_odd(cs)
        # 8. Goal Both Halves
        results["goal_both_halves"] = self._predict_both_halves(X, features)
        # 9. Goal Interval
        results["goal_interval"] = self._predict_goal_interval(X)
        # 10. Player Scorers
        results["player_scorers"] = self._predict_player_scorers(
            home_lineup or [], away_lineup or [],
            goals_pred["home_predicted"], goals_pred["away_predicted"],
        )

        results["features_used"] = features
        results["model_confidence"] = self._compute_confidence(results, features)
        return results

    # ─────────────────────────────────────────────────────────────────────────────
    # Individual prediction methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _predict_1x2(self, X: np.ndarray) -> Dict[str, float]:
        try:
            probs = np.array([
                self._models["home_win"].predict_proba(X)[0][1],
                self._models["draw"].predict_proba(X)[0][1],
                self._models["away_win"].predict_proba(X)[0][1],
            ])
        except Exception:
            probs = np.array([
                float(self._models["home_win"].predict(X)[0]),
                float(self._models["draw"].predict(X)[0]),
                float(self._models["away_win"].predict(X)[0]),
            ])
        probs = np.clip(probs, 0.01, 1.0)
        probs = probs / probs.sum()
        return {
            "home": round(float(probs[0]), 4),
            "draw": round(float(probs[1]), 4),
            "away": round(float(probs[2]), 4),
        }

    def _predict_double_chance(self, match_result: Dict[str, float]) -> Dict[str, float]:
        return {
            "1X": round(match_result["home"] + match_result["draw"], 4),
            "12": round(match_result["home"] + match_result["away"], 4),
            "X2": round(match_result["draw"] + match_result["away"], 4),
        }

    def _predict_btts(self, X: np.ndarray) -> Dict[str, float]:
        try:
            yes = float(self._models["btts"].predict_proba(X)[0][1])
        except Exception:
            yes = float(self._models["btts"].predict(X)[0])
        yes = float(np.clip(yes, 0.01, 0.99))
        return {"yes": round(yes, 4), "no": round(1.0 - yes, 4)}

    def _predict_goals(self, X: np.ndarray, features: Dict) -> Dict[str, Any]:
        raw = self._models["goals_multi"].predict(X)[0]
        raw = np.clip(raw, 0.0, 10.0)
        total = float(raw[0])
        home_g = float(raw[1])
        away_g = float(raw[2])
        total = max(total, home_g + away_g - 0.1)

        thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
        over_under = {}
        for t in thresholds:
            lam = total
            under_prob = sum(poisson.pmf(k, lam) for k in range(int(t + 0.5) + 1))
            under_prob = float(np.clip(under_prob, 0.01, 0.99))
            over_under[f"over_{t}".replace(".5", "_5")] = round(1.0 - under_prob, 4)
            over_under[f"under_{t}".replace(".5", "_5")] = round(under_prob, 4)

        return {
            "predicted": round(total, 2),
            "home_predicted": round(home_g, 2),
            "away_predicted": round(away_g, 2),
            "over_under": over_under,
        }

    def _predict_correct_scores(self, home_lambda: float, away_lambda: float) -> List[Dict]:
        home_lambda = max(0.1, home_lambda)
        away_lambda = max(0.1, away_lambda)
        grid = []
        for h in range(MAX_CORRECT_SCORE + 1):
            for a in range(MAX_CORRECT_SCORE + 1):
                prob = float(poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda))
                grid.append({"home_goals": h, "away_goals": a, "score": f"{h}-{a}", "probability": round(prob, 6)})
        total_prob = sum(g["probability"] for g in grid)
        if total_prob > 0:
            for g in grid:
                g["probability"] = round(g["probability"] / total_prob, 6)
        grid.sort(key=lambda x: x["probability"], reverse=True)
        return grid

    def _predict_score_draw(self, correct_scores: List[Dict]) -> Dict[str, Any]:
        draw_scores = [s for s in correct_scores if s["home_goals"] == s["away_goals"] and s["home_goals"] >= 1]
        prob = sum(s["probability"] for s in draw_scores)
        return {"probability": round(float(prob), 4), "likely_scores": [s["score"] for s in draw_scores[:3]]}

    def _predict_even_odd(self, correct_scores: List[Dict]) -> Dict[str, float]:
        even = sum(s["probability"] for s in correct_scores if (s["home_goals"] + s["away_goals"]) % 2 == 0)
        odd = sum(s["probability"] for s in correct_scores if (s["home_goals"] + s["away_goals"]) % 2 == 1)
        total = even + odd
        return {
            "even": round(float(even / total if total > 0 else 0.5), 4),
            "odd": round(float(odd / total if total > 0 else 0.5), 4),
        }

    def _predict_both_halves(self, X: np.ndarray, features: Dict) -> Dict[str, float]:
        try:
            raw = float(self._models["both_halves"].predict_proba(X)[0][1])
        except Exception:
            raw = float(self._models["both_halves"].predict(X)[0])
        fh_lambda = features.get("home_first_half_goals_avg", 0.6) + features.get("away_first_half_goals_avg", 0.6)
        sh_lambda = features.get("home_second_half_goals_avg", 0.7) + features.get("away_second_half_goals_avg", 0.7)
        heuristic = float(1 - poisson.pmf(0, fh_lambda)) * float(1 - poisson.pmf(0, sh_lambda))
        yes = float(np.clip(0.6 * float(np.clip(raw, 0.0, 1.0)) + 0.4 * heuristic, 0.01, 0.99))
        return {"yes": round(yes, 4), "no": round(1.0 - yes, 4)}

    def _predict_goal_interval(self, X: np.ndarray) -> Dict[str, float]:
        raw = self._models["goal_intervals"].predict(X)[0]
        raw = np.clip(raw, 0.01, 1.0)
        raw = raw / raw.sum()
        labels = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "90+"]
        return {label: round(float(v), 4) for label, v in zip(labels, raw)}

    def _predict_player_scorers(
        self,
        home_lineup: List[Dict],
        away_lineup: List[Dict],
        home_goals_lambda: float,
        away_goals_lambda: float,
    ) -> List[Dict]:
        results = []
        all_players = ([(  "home", p, home_goals_lambda) for p in home_lineup] +
                       [("away", p, away_goals_lambda) for p in away_lineup])

        pos_mult = {
            "ST": 1.0, "CF": 0.95, "LW": 0.7, "RW": 0.7,
            "CAM": 0.45, "CM": 0.3, "CDM": 0.2,
            "LB": 0.1, "RB": 0.1, "CB": 0.08, "GK": 0.01,
        }

        for team, player, team_lambda in all_players:
            position = player.get("position", "CM")
            xg_per90 = float(player.get("xg_per90", 0.2))
            goals_season = float(player.get("goals_season", 3))
            recent_form = float(player.get("recent_form_goals", 1))
            mult = pos_mult.get(position, 0.3)
            base = xg_per90 * 0.4 + (goals_season / 38) * 0.3 + (recent_form / 5) * 0.3
            prob = float(np.clip(base * mult * team_lambda * 0.9, 0.01, 0.95))
            if player.get("penalty_taker", False):
                prob = float(np.clip(prob + 0.08, 0.01, 0.95))
            results.append({
                "player_id": player.get("player_id", ""),
                "name": player.get("name", "Unknown"),
                "position": position,
                "team": team,
                "jersey_no": player.get("jersey_no", 0),
                "probability": round(prob, 4),
                "goals_season": int(goals_season),
                "xg_per90": round(xg_per90, 2),
            })

        results.sort(key=lambda x: x["probability"], reverse=True)
        return results

    # ─────────────────────────────────────────────────────────────────────────────
    # Fallback (untrained model) — unchanged
    # ─────────────────────────────────────────────────────────────────────────────

    def _fallback_predictions(self, features: Dict, home_lineup, away_lineup) -> Dict:
        home_attack = features.get("home_avg_goals_scored_5", 1.3)
        away_attack = features.get("away_avg_goals_scored_5", 1.1)
        home_def = features.get("home_avg_goals_conceded_5", 1.1)
        away_def = features.get("away_avg_goals_conceded_5", 1.2)
        
        # Incorporate league position as a fallback weight
        hp = features.get("home_league_position", 10.0)
        ap = features.get("away_league_position", 10.0)
        pos_weight = (ap - hp) / 20.0 # positive if home is higher (lower number)
        
        home_lambda = max(0.3, (home_attack * 0.7 + (1 / max(away_def, 0.5)) * 0.4 + 0.3) + pos_weight)
        away_lambda = max(0.3, (away_attack * 0.7 + (1 / max(home_def, 0.5)) * 0.4) - pos_weight)

        home_win, draw, away_win = 0.0, 0.0, 0.0
        for h in range(8):
            for a in range(8):
                p = float(poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda))
                if h > a: home_win += p
                elif h == a: draw += p
                else: away_win += p

        total = home_win + draw + away_win
        if total > 0:
            home_win /= total; draw /= total; away_win /= total

        match_result = {"home": round(home_win, 4), "draw": round(draw, 4), "away": round(away_win, 4)}
        cs = self._predict_correct_scores(home_lambda, away_lambda)
        over_under = {}
        for t in [0.5, 1.5, 2.5, 3.5, 4.5]:
            total_goals = home_lambda + away_lambda
            under = sum(poisson.pmf(k, total_goals) for k in range(int(t + 0.5) + 1))
            key = f"over_{t}".replace(".5", "_5")
            out_key = f"under_{t}".replace(".5", "_5")
            over_under[key] = round(float(np.clip(1 - under, 0.01, 0.99)), 4)
            over_under[out_key] = round(float(np.clip(under, 0.01, 0.99)), 4)

        btts_yes = float(np.clip(
            (1 - poisson.pmf(0, home_lambda)) * (1 - poisson.pmf(0, away_lambda)), 0.01, 0.99
        ))
        fh = features.get("home_first_half_goals_avg", 0.6) + features.get("away_first_half_goals_avg", 0.6)
        sh = features.get("home_second_half_goals_avg", 0.7) + features.get("away_second_half_goals_avg", 0.7)

        results = {
            "match_result": match_result,
            "double_chance": self._predict_double_chance(match_result),
            "btts": {"yes": round(btts_yes, 4), "no": round(1.0 - btts_yes, 4)},
            "total_goals": {
                "predicted": round(home_lambda + away_lambda, 2),
                "home_predicted": round(home_lambda, 2),
                "away_predicted": round(away_lambda, 2),
                "over_under": over_under,
            },
            "correct_scores": cs,
            "score_draw": self._predict_score_draw(cs),
            "total_even_odd": self._predict_even_odd(cs),
            "goal_both_halves": {
                "yes": round(float(np.clip(
                    (1 - poisson.pmf(0, fh)) * (1 - poisson.pmf(0, sh)), 0.01, 0.99
                )), 4),
                "no": 0.0,
            },
            "goal_interval": {
                "0-15": 0.12, "16-30": 0.15, "31-45": 0.13,
                "46-60": 0.14, "61-75": 0.16, "76-90": 0.20, "90+": 0.10,
            },
            "player_scorers": self._predict_player_scorers(
                home_lineup or [], away_lineup or [], home_lambda, away_lambda
            ),
            "features_used": features,
            "model_confidence": 0.55,
            "data_source": "heuristic_fallback",
        }
        results["goal_both_halves"]["no"] = round(1.0 - results["goal_both_halves"]["yes"], 4)
        return results

    def _compute_confidence(self, results: Dict, features: Dict) -> float:
        mr = results.get("match_result", {})
        max_prob = max(mr.get("home", 0.33), mr.get("draw", 0.33), mr.get("away", 0.33))
        confidence = 0.5 + (max_prob - 0.33) * 0.8
        return round(min(0.92, max(0.40, confidence)), 3)
