import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any
from config import DEFAULT_ROLLING_WINDOW_SHORT, DEFAULT_ROLLING_WINDOW_LONG


class FootballFeatureEngineer:
    """
    Extracts and engineers features from raw match data for Linear Regression models.
    Handles both API-sourced data and CSV data from football-data.co.uk.
    """

    def __init__(self):
        self.short_window = DEFAULT_ROLLING_WINDOW_SHORT
        self.long_window = DEFAULT_ROLLING_WINDOW_LONG

    # ─────────────────────────────────────────────────────────────────────────────
    # Public: build feature vector for a single upcoming match
    # ─────────────────────────────────────────────────────────────────────────────

    def build_match_features(
        self,
        home_team: str,
        away_team: str,
        match_history: pd.DataFrame,
        home_position: int = 10,
        away_position: int = 10,
        match_importance: float = 1.0,
        home_lineup: Optional[List[Dict]] = None,
        away_lineup: Optional[List[Dict]] = None,
    ) -> Dict[str, float]:
        """
        Build a complete feature dict for a match. Returns default values
        when insufficient history is available.
        """
        df = self._normalize_df(match_history)

        home_matches = self._filter_team_matches(df, home_team)
        away_matches = self._filter_team_matches(df, away_team)
        h2h = self._head_to_head(df, home_team, away_team)

        features: Dict[str, float] = {}

        # ── Goals scored ─────────────────────────────────────────────────────
        features["home_avg_goals_scored_5"] = self._avg_goals_scored(home_matches, home_team, self.short_window)
        features["home_avg_goals_scored_10"] = self._avg_goals_scored(home_matches, home_team, self.long_window)
        features["away_avg_goals_scored_5"] = self._avg_goals_scored(away_matches, away_team, self.short_window)
        features["away_avg_goals_scored_10"] = self._avg_goals_scored(away_matches, away_team, self.long_window)

        # ── Goals conceded ───────────────────────────────────────────────────
        features["home_avg_goals_conceded_5"] = self._avg_goals_conceded(home_matches, home_team, self.short_window)
        features["home_avg_goals_conceded_10"] = self._avg_goals_conceded(home_matches, home_team, self.long_window)
        features["away_avg_goals_conceded_5"] = self._avg_goals_conceded(away_matches, away_team, self.short_window)
        features["away_avg_goals_conceded_10"] = self._avg_goals_conceded(away_matches, away_team, self.long_window)

        # ── Shots on target ──────────────────────────────────────────────────
        features["home_avg_shots_on_target"] = self._avg_shots_on_target(home_matches, home_team, self.short_window)
        features["away_avg_shots_on_target"] = self._avg_shots_on_target(away_matches, away_team, self.short_window)

        # ── Win rates ────────────────────────────────────────────────────────
        features["home_win_rate_10"] = self._win_rate(home_matches, home_team, self.long_window)
        features["away_win_rate_10"] = self._win_rate(away_matches, away_team, self.long_window)

        # ── Form points ──────────────────────────────────────────────────────
        features["home_form_points"] = self._form_points(home_matches, home_team, self.short_window)
        features["away_form_points"] = self._form_points(away_matches, away_team, self.short_window)

        # ── H2H ─────────────────────────────────────────────────────────────
        features["h2h_home_wins"] = self._h2h_result_count(h2h, home_team, "win")
        features["h2h_draws"] = self._h2h_result_count(h2h, home_team, "draw")
        features["h2h_away_wins"] = self._h2h_result_count(h2h, home_team, "loss")

        # ── League position ──────────────────────────────────────────────────
        features["home_league_position"] = float(home_position)
        features["away_league_position"] = float(away_position)

        # ── Half-specific goals ──────────────────────────────────────────────
        features["home_first_half_goals_avg"] = self._avg_half_goals(home_matches, home_team, "first", self.short_window)
        features["away_first_half_goals_avg"] = self._avg_half_goals(away_matches, away_team, "first", self.short_window)
        features["home_second_half_goals_avg"] = self._avg_half_goals(home_matches, home_team, "second", self.short_window)
        features["away_second_half_goals_avg"] = self._avg_half_goals(away_matches, away_team, "second", self.short_window)

        # ── Clean sheet rate ─────────────────────────────────────────────────
        features["home_clean_sheet_rate"] = self._clean_sheet_rate(home_matches, home_team, self.short_window)
        features["away_clean_sheet_rate"] = self._clean_sheet_rate(away_matches, away_team, self.short_window)

        # ── Match importance ─────────────────────────────────────────────────
        features["match_importance_weight"] = float(match_importance)

        # ── Player quality (if lineups provided) ─────────────────────────────
        if home_lineup:
            features["home_avg_xg_per90"] = float(np.mean([p.get("xg_per90", 0.3) for p in home_lineup]))
            features["home_avg_goals_season"] = float(np.mean([p.get("goals_season", 5) for p in home_lineup[:11]]))
        else:
            features["home_avg_xg_per90"] = 0.3
            features["home_avg_goals_season"] = 5.0

        if away_lineup:
            features["away_avg_xg_per90"] = float(np.mean([p.get("xg_per90", 0.3) for p in away_lineup]))
            features["away_avg_goals_season"] = float(np.mean([p.get("goals_season", 5) for p in away_lineup[:11]]))
        else:
            features["away_avg_xg_per90"] = 0.3
            features["away_avg_goals_season"] = 5.0

        return features

    def features_to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to ordered numpy array for model input."""
        return np.array(list(features.values()), dtype=float).reshape(1, -1)

    def get_feature_names(self) -> List[str]:
        """Return ordered list of feature names (matches features_to_array order)."""
        dummy = self.build_match_features("A", "B", pd.DataFrame())
        return list(dummy.keys())

    # ─────────────────────────────────────────────────────────────────────────────
    # Build training dataset from history df
    # ─────────────────────────────────────────────────────────────────────────────

    def build_training_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        For each completed match in df, build features using historical rows
        before it. Returns a DataFrame where each row = one match's features
        plus target columns.
        """
        df = self._normalize_df(df)
        df = df.sort_values("date").reset_index(drop=True)

        rows = []
        for i, row in df.iterrows():
            if i < 20:  # need some history
                continue
            history = df.iloc[:i]
            try:
                feats = self.build_match_features(
                    row["home_team"],
                    row["away_team"],
                    history,
                    match_importance=row.get("match_importance", 1.0),
                )
                # Targets
                feats["target_home_goals"] = float(row["home_goals"])
                feats["target_away_goals"] = float(row["away_goals"])
                feats["target_home_win"] = 1.0 if row["home_goals"] > row["away_goals"] else 0.0
                feats["target_draw"] = 1.0 if row["home_goals"] == row["away_goals"] else 0.0
                feats["target_away_win"] = 1.0 if row["home_goals"] < row["away_goals"] else 0.0
                feats["target_btts"] = 1.0 if (row["home_goals"] > 0 and row["away_goals"] > 0) else 0.0
                feats["target_both_halves"] = float(
                    row.get("home_ht_goals", 0) + row.get("away_ht_goals", 0) > 0
                    and (row["home_goals"] - row.get("home_ht_goals", 0))
                    + (row["away_goals"] - row.get("away_ht_goals", 0)) > 0
                )
                feats["target_first_half_goals"] = float(
                    row.get("home_ht_goals", 0) + row.get("away_ht_goals", 0)
                )
                rows.append(feats)
            except Exception:
                continue

        return pd.DataFrame(rows)

    # ─────────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names across API and CSV sources."""
        if df.empty:
            return pd.DataFrame(columns=[
                "date", "home_team", "away_team",
                "home_goals", "away_goals",
                "home_ht_goals", "away_ht_goals",
                "home_shots_on_target", "away_shots_on_target",
            ])
        col_map = {
            # CSV (football-data.co.uk) → internal
            "HomeTeam": "home_team", "AwayTeam": "away_team",
            "FTHG": "home_goals", "FTAG": "away_goals",
            "HTHG": "home_ht_goals", "HTAG": "away_ht_goals",
            "HST": "home_shots_on_target", "AST": "away_shots_on_target",
            "Date": "date",
            # API (football-data.org) already maps via _parse_api_match
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ["home_goals", "away_goals", "home_ht_goals", "away_ht_goals",
                    "home_shots_on_target", "away_shots_on_target"]:
            if col not in df.columns:
                df[col] = 0
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    @staticmethod
    def _filter_team_matches(df: pd.DataFrame, team: str, n: int = 50) -> pd.DataFrame:
        mask = (df["home_team"] == team) | (df["away_team"] == team)
        return df[mask].tail(n)

    @staticmethod
    def _head_to_head(df: pd.DataFrame, home: str, away: str, n: int = 5) -> pd.DataFrame:
        mask = (
            ((df["home_team"] == home) & (df["away_team"] == away)) |
            ((df["home_team"] == away) & (df["away_team"] == home))
        )
        return df[mask].tail(n)

    def _avg_goals_scored(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 1.2
        recent = matches.tail(window)
        goals = []
        for _, r in recent.iterrows():
            if r["home_team"] == team:
                goals.append(r["home_goals"])
            else:
                goals.append(r["away_goals"])
        return float(np.mean(goals)) if goals else 1.2

    def _avg_goals_conceded(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 1.2
        recent = matches.tail(window)
        goals = []
        for _, r in recent.iterrows():
            if r["home_team"] == team:
                goals.append(r["away_goals"])
            else:
                goals.append(r["home_goals"])
        return float(np.mean(goals)) if goals else 1.2

    def _avg_shots_on_target(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 4.5
        recent = matches.tail(window)
        shots = []
        for _, r in recent.iterrows():
            col = "home_shots_on_target" if r["home_team"] == team else "away_shots_on_target"
            if col in r.index and not pd.isna(r[col]):
                shots.append(float(r[col]))
        return float(np.mean(shots)) if shots else 4.5

    def _win_rate(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 0.35
        recent = matches.tail(window)
        wins = 0
        for _, r in recent.iterrows():
            if r["home_team"] == team and r["home_goals"] > r["away_goals"]:
                wins += 1
            elif r["away_team"] == team and r["away_goals"] > r["home_goals"]:
                wins += 1
        return wins / len(recent) if len(recent) > 0 else 0.35

    def _form_points(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 5.0
        recent = matches.tail(window)
        points = 0.0
        for _, r in recent.iterrows():
            if r["home_team"] == team:
                scored, conceded = r["home_goals"], r["away_goals"]
            else:
                scored, conceded = r["away_goals"], r["home_goals"]
            if scored > conceded:
                points += 3
            elif scored == conceded:
                points += 1
        return float(points)

    def _h2h_result_count(self, h2h: pd.DataFrame, home_team: str, result_type: str) -> float:
        if h2h.empty:
            return {"win": 2.0, "draw": 1.0, "loss": 2.0}[result_type]
        count = 0
        for _, r in h2h.iterrows():
            if r["home_team"] == home_team:
                scored, conceded = r["home_goals"], r["away_goals"]
            else:
                scored, conceded = r["away_goals"], r["home_goals"]
            if result_type == "win" and scored > conceded:
                count += 1
            elif result_type == "draw" and scored == conceded:
                count += 1
            elif result_type == "loss" and scored < conceded:
                count += 1
        return float(count)

    def _avg_half_goals(self, matches: pd.DataFrame, team: str, half: str, window: int) -> float:
        if matches.empty:
            return 0.6
        recent = matches.tail(window)
        if half == "first":
            home_col, away_col = "home_ht_goals", "away_ht_goals"
        else:
            home_col, away_col = None, None

        goals = []
        for _, r in recent.iterrows():
            if half == "first":
                g = r.get("home_ht_goals", 0) + r.get("away_ht_goals", 0)
                if r["home_team"] == team:
                    goals.append(float(r.get("home_ht_goals", 0.6)))
                else:
                    goals.append(float(r.get("away_ht_goals", 0.6)))
            else:
                ht = r.get("home_ht_goals", 0) if r["home_team"] == team else r.get("away_ht_goals", 0)
                ft = r["home_goals"] if r["home_team"] == team else r["away_goals"]
                goals.append(max(0.0, float(ft) - float(ht)))
        return float(np.mean(goals)) if goals else 0.6

    def _clean_sheet_rate(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 0.3
        recent = matches.tail(window)
        clean_sheets = 0
        for _, r in recent.iterrows():
            conceded = r["away_goals"] if r["home_team"] == team else r["home_goals"]
            if conceded == 0:
                clean_sheets += 1
        return clean_sheets / len(recent) if len(recent) > 0 else 0.3
