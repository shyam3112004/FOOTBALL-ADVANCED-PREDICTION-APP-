import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any
from config import DEFAULT_ROLLING_WINDOW_SHORT, DEFAULT_ROLLING_WINDOW_LONG


class FootballFeatureEngineer:
    """
    Extracts and engineers features from raw match data for XGBoost models.
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
        home_team_id: Optional[int] = None,
        away_team_id: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Build a complete feature dict for a match. Returns default values
        when insufficient history is available.
        """
        df = self._normalize_df(match_history)

        home_matches = self._filter_team_matches(df, home_team, team_id=home_team_id)
        away_matches = self._filter_team_matches(df, away_team, team_id=away_team_id)
        h2h = self._head_to_head(df, home_team, away_team, home_id=home_team_id, away_id=away_team_id)

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
    # Build training dataset — VECTORIZED (runs <2s on 500 matches)
    # ─────────────────────────────────────────────────────────────────────────────

    def build_training_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        For each completed match in df, build features using historical rows
        before it.  Uses vectorized rolling operations instead of row-by-row
        iteration for O(n log n) complexity.
        """
        df = self._normalize_df(df)
        df = df.sort_values("date").reset_index(drop=True)

        if len(df) < 20:
            return pd.DataFrame()

        # ── STEP 1: compute per-row team perspective metrics using groupby+rolling ──
        rows_home = self._compute_team_rolling_stats(df, perspective="home")
        rows_away = self._compute_team_rolling_stats(df, perspective="away")

        # ── STEP 2: merge home/away stats back onto the match dataframe ──────────
        df = df.join(rows_home, rsuffix="_h_stat")
        df = df.join(rows_away, rsuffix="_a_stat")

        # Skip first 20 rows (insufficient history for either team)
        df = df.iloc[20:].copy()

        # ── STEP 3: build target columns ─────────────────────────────────────────
        df["target_home_goals"] = df["home_goals"].astype(float)
        df["target_away_goals"] = df["away_goals"].astype(float)
        df["target_home_win"] = (df["home_goals"] > df["away_goals"]).astype(float)
        df["target_draw"] = (df["home_goals"] == df["away_goals"]).astype(float)
        df["target_away_win"] = (df["home_goals"] < df["away_goals"]).astype(float)
        df["target_btts"] = (
            (df["home_goals"] > 0) & (df["away_goals"] > 0)
        ).astype(float)

        home_ht = df.get("home_ht_goals", pd.Series(0, index=df.index)).fillna(0)
        away_ht = df.get("away_ht_goals", pd.Series(0, index=df.index)).fillna(0)
        fh_goals = home_ht + away_ht
        sh_goals = (df["home_goals"] - home_ht) + (df["away_goals"] - away_ht)
        df["target_both_halves"] = ((fh_goals > 0) & (sh_goals > 0)).astype(float)
        df["target_first_half_goals"] = fh_goals.astype(float)

        # ── STEP 4: gather H2H stats per row (small vectorized loop by pair) ─────
        h2h_cols = self._vectorized_h2h(df)
        df = df.join(h2h_cols)

        # ── STEP 5: assemble final feature rows ───────────────────────────────────
        feature_cols = self.get_feature_names()
        target_cols = [
            "target_home_goals", "target_away_goals",
            "target_home_win", "target_draw", "target_away_win",
            "target_btts", "target_both_halves", "target_first_half_goals",
        ]

        # Map computed rolling columns to feature names
        col_map = self._get_column_map()
        df = df.rename(columns=col_map)

        # Add defaults for missing feature columns
        for col in feature_cols:
            if col not in df.columns:
                df[col] = self._default_for_feature(col)

        df["match_importance_weight"] = df.get("match_importance", pd.Series(1.0, index=df.index)).fillna(1.0)
        df["home_avg_xg_per90"] = 0.3
        df["home_avg_goals_season"] = 5.0
        df["away_avg_xg_per90"] = 0.3
        df["away_avg_goals_season"] = 5.0

        available_cols = [c for c in feature_cols + target_cols if c in df.columns]
        result = df[available_cols].fillna(0)
        return result.reset_index(drop=True)

    def _compute_team_rolling_stats(self, df: pd.DataFrame, perspective: str) -> pd.DataFrame:
        """
        Compute rolling statistics from each team's perspective.
        perspective="home" → stats calculated for the home team in each row.
        perspective="away" → stats calculated for the away team.
        """
        prefix = "home" if perspective == "home" else "away"
        opp_prefix = "away" if perspective == "home" else "home"
        team_col = f"{prefix}_team"

        goal_col = f"{prefix}_goals"
        opp_goal_col = f"{opp_prefix}_goals"
        ht_col = f"{prefix}_ht_goals"
        sot_col = f"{prefix}_shots_on_target"

        out_rows = []
        # We process team by team for correct per-team rolling calculations
        for team, gdf in df.groupby(team_col):
            g = gdf.copy()
            goals = g[goal_col].astype(float)
            opp_goals = g[opp_goal_col].astype(float)
            ht_goals = g.get(ht_col, pd.Series(0, index=g.index)).astype(float).fillna(0)
            sot = g.get(sot_col, pd.Series(np.nan, index=g.index)).astype(float)
            win_flag = (goals > opp_goals).astype(float)
            pts = win_flag * 3 + ((goals == opp_goals).astype(float))
            cs_flag = (opp_goals == 0).astype(float)
            sh_goals = (goals - ht_goals).clip(lower=0)

            w_short = self.short_window
            w_long = self.long_window

            g[f"{prefix}_avg_goals_scored_5"] = goals.shift(1).rolling(w_short, min_periods=1).mean().fillna(1.2)
            g[f"{prefix}_avg_goals_scored_10"] = goals.shift(1).rolling(w_long, min_periods=1).mean().fillna(1.2)
            g[f"{prefix}_avg_goals_conceded_5"] = opp_goals.shift(1).rolling(w_short, min_periods=1).mean().fillna(1.2)
            g[f"{prefix}_avg_goals_conceded_10"] = opp_goals.shift(1).rolling(w_long, min_periods=1).mean().fillna(1.2)
            g[f"{prefix}_avg_shots_on_target"] = sot.shift(1).rolling(w_short, min_periods=1).mean().fillna(4.5)
            g[f"{prefix}_win_rate_10"] = win_flag.shift(1).rolling(w_long, min_periods=1).mean().fillna(0.35)
            g[f"{prefix}_form_points"] = pts.shift(1).rolling(w_short, min_periods=1).sum().fillna(5.0)
            g[f"{prefix}_clean_sheet_rate"] = cs_flag.shift(1).rolling(w_short, min_periods=1).mean().fillna(0.3)
            g[f"{prefix}_first_half_goals_avg"] = ht_goals.shift(1).rolling(w_short, min_periods=1).mean().fillna(0.6)
            g[f"{prefix}_second_half_goals_avg"] = sh_goals.shift(1).rolling(w_short, min_periods=1).mean().fillna(0.6)

            out_rows.append(g[[
                f"{prefix}_avg_goals_scored_5",
                f"{prefix}_avg_goals_scored_10",
                f"{prefix}_avg_goals_conceded_5",
                f"{prefix}_avg_goals_conceded_10",
                f"{prefix}_avg_shots_on_target",
                f"{prefix}_win_rate_10",
                f"{prefix}_form_points",
                f"{prefix}_clean_sheet_rate",
                f"{prefix}_first_half_goals_avg",
                f"{prefix}_second_half_goals_avg",
            ]])

        if out_rows:
            result = pd.concat(out_rows).sort_index()
            # Deduplicate index (each row appears once for home, once for away)
            result = result[~result.index.duplicated(keep="first")]
            return result
        return pd.DataFrame(index=df.index)

    def _vectorized_h2h(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute H2H wins/draws/losses for each match using cumulative
        counts up to (but not including) each row.
        """
        h2h_home_wins = []
        h2h_draws = []
        h2h_away_wins = []

        for idx, row in df.iterrows():
            ht, at = row["home_team"], row["away_team"]
            past = df.loc[:idx].iloc[:-1]  # rows before current
            h2h = past[
                ((past["home_team"] == ht) & (past["away_team"] == at)) |
                ((past["home_team"] == at) & (past["away_team"] == ht))
            ].tail(5)
            wins = draws = losses = 0
            for _, r in h2h.iterrows():
                if r["home_team"] == ht:
                    s, c = r["home_goals"], r["away_goals"]
                else:
                    s, c = r["away_goals"], r["home_goals"]
                if s > c:
                    wins += 1
                elif s == c:
                    draws += 1
                else:
                    losses += 1
            h2h_home_wins.append(wins)
            h2h_draws.append(draws)
            h2h_away_wins.append(losses)

        return pd.DataFrame(
            {
                "h2h_home_wins": h2h_home_wins,
                "h2h_draws": h2h_draws,
                "h2h_away_wins": h2h_away_wins,
            },
            index=df.index,
        )

    @staticmethod
    def _get_column_map() -> dict:
        """Map computed column names to feature names expected by the model."""
        return {
            "home_first_half_goals_avg": "home_first_half_goals_avg",
            "away_first_half_goals_avg": "away_first_half_goals_avg",
            "home_second_half_goals_avg": "home_second_half_goals_avg",
            "away_second_half_goals_avg": "away_second_half_goals_avg",
        }

    @staticmethod
    def _default_for_feature(col: str) -> float:
        """Sensible default values per feature name."""
        defaults = {
            "home_avg_goals_scored_5": 1.2,
            "home_avg_goals_scored_10": 1.2,
            "away_avg_goals_scored_5": 1.2,
            "away_avg_goals_scored_10": 1.2,
            "home_avg_goals_conceded_5": 1.2,
            "home_avg_goals_conceded_10": 1.2,
            "away_avg_goals_conceded_5": 1.2,
            "away_avg_goals_conceded_10": 1.2,
            "home_avg_shots_on_target": 4.5,
            "away_avg_shots_on_target": 4.5,
            "home_win_rate_10": 0.35,
            "away_win_rate_10": 0.35,
            "home_form_points": 5.0,
            "away_form_points": 5.0,
            "h2h_home_wins": 2.0,
            "h2h_draws": 1.0,
            "h2h_away_wins": 2.0,
            "home_league_position": 10.0,
            "away_league_position": 10.0,
            "home_first_half_goals_avg": 0.6,
            "away_first_half_goals_avg": 0.6,
            "home_second_half_goals_avg": 0.6,
            "away_second_half_goals_avg": 0.6,
            "home_clean_sheet_rate": 0.3,
            "away_clean_sheet_rate": 0.3,
            "match_importance_weight": 1.0,
            "home_avg_xg_per90": 0.3,
            "home_avg_goals_season": 5.0,
            "away_avg_xg_per90": 0.3,
            "away_avg_goals_season": 5.0,
        }
        return defaults.get(col, 0.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Private helpers (used by build_match_features for single-match prediction)
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
            "HomeTeam": "home_team", "AwayTeam": "away_team",
            "FTHG": "home_goals", "FTAG": "away_goals",
            "HTHG": "home_ht_goals", "HTAG": "away_ht_goals",
            "HST": "home_shots_on_target", "AST": "away_shots_on_target",
            "Date": "date",
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
    def _filter_team_matches(df: pd.DataFrame, team: str, n: int = 50, team_id: Optional[int] = None) -> pd.DataFrame:
        if team_id is not None and "home_team_id" in df.columns:
            mask = (df["home_team_id"] == team_id) | (df["away_team_id"] == team_id)
        else:
            mask = (df["home_team"] == team) | (df["away_team"] == team)
        return df[mask].tail(n)

    @staticmethod
    def _head_to_head(df: pd.DataFrame, home: str, away: str, n: int = 5, home_id: Optional[int] = None, away_id: Optional[int] = None) -> pd.DataFrame:
        if home_id is not None and away_id is not None and "home_team_id" in df.columns:
            mask = (
                ((df["home_team_id"] == home_id) & (df["away_team_id"] == away_id)) |
                ((df["home_team_id"] == away_id) & (df["away_team_id"] == home_id))
            )
        else:
            mask = (
                ((df["home_team"] == home) & (df["away_team"] == away)) |
                ((df["home_team"] == away) & (df["away_team"] == home))
            )
        return df[mask].tail(n)

    def _avg_goals_scored(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 1.2
        recent = matches.tail(window)
        goals = np.where(recent["home_team"] == team, recent["home_goals"], recent["away_goals"])
        return float(np.mean(goals)) if len(goals) > 0 else 1.2

    def _avg_goals_conceded(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 1.2
        recent = matches.tail(window)
        goals = np.where(recent["home_team"] == team, recent["away_goals"], recent["home_goals"])
        return float(np.mean(goals)) if len(goals) > 0 else 1.2

    def _avg_shots_on_target(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 4.5
        recent = matches.tail(window)
        col = np.where(recent["home_team"] == team, "home_shots_on_target", "away_shots_on_target")
        shots = [float(row[col[i]]) for i, (_, row) in enumerate(recent.iterrows())
                 if col[i] in row.index and not pd.isna(row[col[i]])]
        return float(np.mean(shots)) if shots else 4.5

    def _win_rate(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 0.35
        recent = matches.tail(window)
        is_home = recent["home_team"] == team
        wins = ((is_home) & (recent["home_goals"] > recent["away_goals"])) | \
               ((~is_home) & (recent["away_goals"] > recent["home_goals"]))
        return float(wins.sum() / len(recent)) if len(recent) > 0 else 0.35

    def _form_points(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 5.0
        recent = matches.tail(window)
        is_home = recent["home_team"] == team
        scored = np.where(is_home, recent["home_goals"], recent["away_goals"])
        conceded = np.where(is_home, recent["away_goals"], recent["home_goals"])
        pts = np.where(scored > conceded, 3, np.where(scored == conceded, 1, 0))
        return float(pts.sum())

    def _h2h_result_count(self, h2h: pd.DataFrame, home_team: str, result_type: str) -> float:
        if h2h.empty:
            return {"win": 2.0, "draw": 1.0, "loss": 2.0}[result_type]
        is_home = h2h["home_team"] == home_team
        scored = np.where(is_home, h2h["home_goals"], h2h["away_goals"])
        conceded = np.where(is_home, h2h["away_goals"], h2h["home_goals"])
        if result_type == "win":
            return float((scored > conceded).sum())
        elif result_type == "draw":
            return float((scored == conceded).sum())
        return float((scored < conceded).sum())

    def _avg_half_goals(self, matches: pd.DataFrame, team: str, half: str, window: int) -> float:
        if matches.empty:
            return 0.6
        recent = matches.tail(window)
        is_home = recent["home_team"] == team
        if half == "first":
            goals = np.where(
                is_home,
                recent.get("home_ht_goals", pd.Series(0.6, index=recent.index)).fillna(0.6),
                recent.get("away_ht_goals", pd.Series(0.6, index=recent.index)).fillna(0.6),
            )
        else:
            ht = np.where(
                is_home,
                recent.get("home_ht_goals", pd.Series(0, index=recent.index)).fillna(0),
                recent.get("away_ht_goals", pd.Series(0, index=recent.index)).fillna(0),
            )
            ft = np.where(is_home, recent["home_goals"], recent["away_goals"])
            goals = np.maximum(0, ft.astype(float) - ht.astype(float))
        return float(np.mean(goals)) if len(goals) > 0 else 0.6

    def _clean_sheet_rate(self, matches: pd.DataFrame, team: str, window: int) -> float:
        if matches.empty:
            return 0.3
        recent = matches.tail(window)
        is_home = recent["home_team"] == team
        conceded = np.where(is_home, recent["away_goals"], recent["home_goals"])
        return float((conceded == 0).sum() / len(recent)) if len(recent) > 0 else 0.3
