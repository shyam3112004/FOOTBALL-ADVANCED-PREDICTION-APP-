import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import LinearRegression
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from typing import Dict, List, Any, Optional, Tuple

from models.feature_engineering import FootballFeatureEngineer
from config import MAX_CORRECT_SCORE, MIN_MATCHES_FOR_TRAINING


class FootballPredictor:
    """
    Wraps all 10 Linear Regression prediction models for football match outcomes.
    Trains on historical match data and predicts probabilities for upcoming fixtures.
    """

    def __init__(self):
        self.feature_engineer = FootballFeatureEngineer()
        self.is_trained = False
        self.training_samples = 0

        # Model pipelines (StandardScaler + LinearRegression)
        self._models: Dict[str, Any] = {}
        self._init_models()

    # ─────────────────────────────────────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────────────────────────────────────

    def _init_models(self):
        """Initialize all model pipelines."""
        def make_pipeline():
            return Pipeline([
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ])

        def make_multi_pipeline():
            return Pipeline([
                ("scaler", StandardScaler()),
                ("model", MultiOutputRegressor(LinearRegression())),
            ])

        self._models = {
            "home_win": make_pipeline(),
            "draw": make_pipeline(),
            "away_win": make_pipeline(),
            "btts": make_pipeline(),
            "goals_multi": make_multi_pipeline(),  # [total, home, away]
            "both_halves": make_pipeline(),
            "goal_intervals": make_multi_pipeline(),  # 7 intervals
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Training
    # ─────────────────────────────────────────────────────────────────────────────

    def train(self, match_history: pd.DataFrame) -> Dict[str, Any]:
        """Train all models from historical match data."""
        training_df = self.feature_engineer.build_training_data(match_history)

        if len(training_df) < MIN_MATCHES_FOR_TRAINING:
            return {
                "status": "insufficient_data",
                "samples": len(training_df),
                "required": MIN_MATCHES_FOR_TRAINING,
            }

        feature_cols = self.feature_engineer.get_feature_names()
        # Only keep columns that exist in training_df
        feature_cols = [c for c in feature_cols if c in training_df.columns]
        X = training_df[feature_cols].fillna(0).values

        self.training_samples = len(training_df)

        # ── Result models ────────────────────────────────────────────────────
        for target, model_key in [
            ("target_home_win", "home_win"),
            ("target_draw", "draw"),
            ("target_away_win", "away_win"),
            ("target_btts", "btts"),
            ("target_both_halves", "both_halves"),
        ]:
            if target in training_df.columns:
                y = training_df[target].fillna(0.5).values
                self._models[model_key].fit(X, y)

        # ── Goals multi-output ───────────────────────────────────────────────
        goal_targets = ["target_home_goals", "target_away_goals"]
        if all(c in training_df.columns for c in goal_targets):
            y_goals = training_df[goal_targets].fillna(1.2).values
            total = y_goals[:, 0] + y_goals[:, 1]
            y_goals_full = np.column_stack([total, y_goals[:, 0], y_goals[:, 1]])
            self._models["goals_multi"].fit(X, y_goals_full)

        # ── Goal intervals (synthetic from half data) ────────────────────────
        if "target_first_half_goals" in training_df.columns:
            y_intervals = self._synthesize_intervals(training_df)
            self._models["goal_intervals"].fit(X, y_intervals)

        self.is_trained = True
        return {"status": "trained", "samples": self.training_samples}

    def _synthesize_intervals(self, df: pd.DataFrame) -> np.ndarray:
        """
        Approximate interval probabilities from halftime goal data.
        Distributes goals across 7 time intervals using historical patterns.
        """
        n = len(df)
        # Expected distribution across intervals (research-based priors)
        prior = np.array([0.12, 0.15, 0.13, 0.14, 0.16, 0.20, 0.10])
        y = np.tile(prior, (n, 1))

        if "target_first_half_goals" in df.columns:
            fhg = df["target_first_half_goals"].fillna(0).clip(0, 5)
            total = (df.get("target_home_goals", 1.2) + df.get("target_away_goals", 1.2)).fillna(2.4)
            fh_ratio = (fhg / total.replace(0, 2.4)).clip(0, 1)
            # Scale first 3 intervals by first-half ratio
            for i in range(3):
                y[:, i] = y[:, i] * (fh_ratio * 2)
            # Renormalize
            row_sums = y.sum(axis=1, keepdims=True)
            y = y / np.where(row_sums == 0, 1, row_sums)

        return y

    # ─────────────────────────────────────────────────────────────────────────────
    # Prediction (all 10 categories)
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
    ) -> Dict[str, Any]:
        """Run all 10 predictions for a given match."""
        features = self.feature_engineer.build_match_features(
            home_team, away_team, match_history,
            home_position, away_position, match_importance,
            home_lineup, away_lineup,
        )
        X = self.feature_engineer.features_to_array(features)

        if not self.is_trained:
            return self._fallback_predictions(features, home_lineup, away_lineup)

        results = {}

        # 1. 1X2 ──────────────────────────────────────────────────────────────
        results["match_result"] = self._predict_1x2(X)

        # 2. Double Chance (derived) ──────────────────────────────────────────
        results["double_chance"] = self._predict_double_chance(results["match_result"])

        # 3. BTTS ─────────────────────────────────────────────────────────────
        results["btts"] = self._predict_btts(X)

        # 4. Total Goals (multi-output) ───────────────────────────────────────
        goals_pred = self._predict_goals(X, features)
        results["total_goals"] = goals_pred

        # 5. Correct Score (Poisson) ──────────────────────────────────────────
        cs = self._predict_correct_scores(
            goals_pred["home_predicted"], goals_pred["away_predicted"]
        )
        results["correct_scores"] = cs

        # 6. Score Draw ───────────────────────────────────────────────────────
        results["score_draw"] = self._predict_score_draw(cs)

        # 7. Total Even/Odd ───────────────────────────────────────────────────
        results["total_even_odd"] = self._predict_even_odd(cs)

        # 8. Goal in Both Halves ──────────────────────────────────────────────
        results["goal_both_halves"] = self._predict_both_halves(X, features)

        # 9. Goal Interval ────────────────────────────────────────────────────
        results["goal_interval"] = self._predict_goal_interval(X)

        # 10. Player Scorers ──────────────────────────────────────────────────
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
        raw = np.array([
            float(self._models["home_win"].predict(X)[0]),
            float(self._models["draw"].predict(X)[0]),
            float(self._models["away_win"].predict(X)[0]),
        ])
        raw = np.clip(raw, 0.01, 1.0)
        probs = raw / raw.sum()
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
        raw = float(self._models["btts"].predict(X)[0])
        yes = float(np.clip(raw, 0.01, 0.99))
        return {"yes": round(yes, 4), "no": round(1.0 - yes, 4)}

    def _predict_goals(self, X: np.ndarray, features: Dict) -> Dict[str, Any]:
        raw = self._models["goals_multi"].predict(X)[0]
        raw = np.clip(raw, 0.0, 10.0)
        total = float(raw[0])
        home_g = float(raw[1])
        away_g = float(raw[2])

        # Ensure internal consistency
        total = max(total, home_g + away_g - 0.1)

        thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
        over_under = {}
        for t in thresholds:
            # Poisson-based probability of exceeding threshold
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
                grid.append({
                    "home_goals": h,
                    "away_goals": a,
                    "score": f"{h}-{a}",
                    "probability": round(prob, 6),
                })
        # Normalize
        total_prob = sum(g["probability"] for g in grid)
        if total_prob > 0:
            for g in grid:
                g["probability"] = round(g["probability"] / total_prob, 6)
        grid.sort(key=lambda x: x["probability"], reverse=True)
        return grid

    def _predict_score_draw(self, correct_scores: List[Dict]) -> Dict[str, Any]:
        draw_scores = [
            s for s in correct_scores
            if s["home_goals"] == s["away_goals"] and s["home_goals"] >= 1
        ]
        prob = sum(s["probability"] for s in draw_scores)
        likely = [s["score"] for s in draw_scores[:3]]
        return {
            "probability": round(float(prob), 4),
            "likely_scores": likely,
        }

    def _predict_even_odd(self, correct_scores: List[Dict]) -> Dict[str, float]:
        even = sum(s["probability"] for s in correct_scores
                   if (s["home_goals"] + s["away_goals"]) % 2 == 0)
        odd = sum(s["probability"] for s in correct_scores
                  if (s["home_goals"] + s["away_goals"]) % 2 == 1)
        total = even + odd
        return {
            "even": round(float(even / total if total > 0 else 0.5), 4),
            "odd": round(float(odd / total if total > 0 else 0.5), 4),
        }

    def _predict_both_halves(self, X: np.ndarray, features: Dict) -> Dict[str, float]:
        raw = float(self._models["both_halves"].predict(X)[0])
        # Blend with feature-based heuristic
        fh_lambda = features.get("home_first_half_goals_avg", 0.6) + features.get("away_first_half_goals_avg", 0.6)
        sh_lambda = features.get("home_second_half_goals_avg", 0.7) + features.get("away_second_half_goals_avg", 0.7)
        p_fh = float(1 - poisson.pmf(0, fh_lambda))
        p_sh = float(1 - poisson.pmf(0, sh_lambda))
        heuristic = p_fh * p_sh
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
        all_players = [("home", p, home_goals_lambda) for p in home_lineup] + \
                      [("away", p, away_goals_lambda) for p in away_lineup]

        for team, player, team_lambda in all_players:
            position = player.get("position", "CM")
            xg_per90 = float(player.get("xg_per90", 0.2))
            goals_season = float(player.get("goals_season", 3))
            recent_form = float(player.get("recent_form_goals", 1))

            # Position multipliers
            pos_mult = {
                "ST": 1.0, "CF": 0.95, "LW": 0.7, "RW": 0.7,
                "CAM": 0.45, "CM": 0.3, "CDM": 0.2,
                "LB": 0.1, "RB": 0.1, "CB": 0.08, "GK": 0.01,
            }.get(position, 0.3)

            # Combine signals
            base = xg_per90 * 0.4 + (goals_season / 38) * 0.3 + (recent_form / 5) * 0.3
            prob = float(np.clip(
                base * pos_mult * team_lambda * 0.9,
                0.01, 0.95
            ))

            # Penalty bonus
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
    # Fallback (untrained model) using heuristics only
    # ─────────────────────────────────────────────────────────────────────────────

    def _fallback_predictions(self, features: Dict, home_lineup, away_lineup) -> Dict:
        """Generate heuristic-based predictions when model isn't trained."""
        home_attack = features.get("home_avg_goals_scored_5", 1.3)
        away_attack = features.get("away_avg_goals_scored_5", 1.1)
        home_def = features.get("home_avg_goals_conceded_5", 1.1)
        away_def = features.get("away_avg_goals_conceded_5", 1.2)

        # Estimated lambdas (Dixon-Coles style approximation)
        home_lambda = max(0.3, home_attack * 0.7 + (1 / max(away_def, 0.5)) * 0.4 + 0.3)
        away_lambda = max(0.3, away_attack * 0.7 + (1 / max(home_def, 0.5)) * 0.4)

        # Simulate via Poisson
        home_win, draw, away_win = 0.0, 0.0, 0.0
        for h in range(8):
            for a in range(8):
                p = float(poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda))
                if h > a:
                    home_win += p
                elif h == a:
                    draw += p
                else:
                    away_win += p

        total = home_win + draw + away_win
        if total > 0:
            home_win /= total; draw /= total; away_win /= total

        match_result = {
            "home": round(home_win, 4),
            "draw": round(draw, 4),
            "away": round(away_win, 4),
        }
        cs = self._predict_correct_scores(home_lambda, away_lambda)
        over_under = {}
        for t in [0.5, 1.5, 2.5, 3.5, 4.5]:
            total_goals = home_lambda + away_lambda
            under = sum(poisson.pmf(k, total_goals) for k in range(int(t + 0.5) + 1))
            key = f"over_{t}".replace(".5", "_5")
            out_key = f"under_{t}".replace(".5", "_5")
            over_under[key] = round(float(np.clip(1 - under, 0.01, 0.99)), 4)
            over_under[out_key] = round(float(np.clip(under, 0.01, 0.99)), 4)

        # BTTS heuristic
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
                "yes": round(float(np.clip((1 - poisson.pmf(0, fh)) * (1 - poisson.pmf(0, sh)), 0.01, 0.99)), 4),
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
        """Estimate model confidence based on prediction spread and data quality."""
        mr = results.get("match_result", {})
        max_prob = max(mr.get("home", 0.33), mr.get("draw", 0.33), mr.get("away", 0.33))
        # More decisive predictions → slightly higher confidence
        confidence = 0.5 + (max_prob - 0.33) * 0.8
        confidence = min(0.92, max(0.40, confidence))
        return round(confidence, 3)
