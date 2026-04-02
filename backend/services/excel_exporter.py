import io
from datetime import datetime
from typing import Dict, List, Any, Optional

import openpyxl
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side,
    GradientFill
)
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
from openpyxl.chart import BarChart, Reference


# ─── Color constants ──────────────────────────────────────────────────────────
DARK_GREEN  = "00703C"
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
HEADER_FILL = PatternFill(start_color=DARK_GREEN, end_color=DARK_GREEN, fill_type="solid")
ALT_FILL    = PatternFill(start_color="F2F7F4", end_color="F2F7F4", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)
HIGH_FILL   = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
MED_FILL    = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
LOW_FILL    = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")


def _header_row(ws, row: int, values: List[str], freeze: bool = False):
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[row].height = 22
    if freeze:
        ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _data_row(ws, row: int, values: List[Any], alt: bool = False):
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
        if alt:
            cell.fill = ALT_FILL


def _pct_row(ws, row: int, values: List[Any], alt: bool = False):
    """Same as _data_row but percentage columns formatted."""
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
        if alt:
            cell.fill = ALT_FILL
        if isinstance(val, float) and 0 <= val <= 1:
            cell.number_format = "0.00%"


def _autofit(ws):
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 32)


def _add_conditional_formatting(ws, col_letter: str, start_row: int, end_row: int):
    """Green >60%, amber 40-60%, red <40% for probability columns."""
    pct_range = f"{col_letter}{start_row}:{col_letter}{end_row}"
    ws.conditional_formatting.add(pct_range, CellIsRule(
        operator="greaterThan", formula=["0.6"], fill=HIGH_FILL
    ))
    ws.conditional_formatting.add(pct_range, CellIsRule(
        operator="between", formula=["0.4", "0.6"], fill=MED_FILL
    ))
    ws.conditional_formatting.add(pct_range, CellIsRule(
        operator="lessThan", formula=["0.4"], fill=LOW_FILL
    ))


class ExcelExporter:
    """
    Generates multi-sheet Excel workbook with prediction results.
    Uses openpyxl with dark green headers, alternating rows, conditional formatting.
    """

    def export(self, prediction_data: Dict, match_info: Dict) -> bytes:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # remove default sheet

        self._sheet_overview(wb, match_info, prediction_data)
        self._sheet_1x2_double_chance(wb, prediction_data)
        self._sheet_goals(wb, prediction_data)
        self._sheet_correct_scores(wb, prediction_data)
        self._sheet_specials(wb, prediction_data)
        self._sheet_player_scorers(wb, prediction_data)
        self._sheet_raw_features(wb, prediction_data)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 1: Match Overview
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_overview(self, wb, match_info: Dict, pred: Dict):
        ws = wb.create_sheet("Match Overview")
        row = 1

        ws.merge_cells(f"A{row}:F{row}")
        title = ws.cell(row=row, column=1, value="⚽ FOOTBALL PREDICTION REPORT")
        title.font = Font(bold=True, size=16, color="FFFFFF", name="Calibri")
        title.fill = PatternFill(start_color="0A0E1A", end_color="0A0E1A", fill_type="solid")
        title.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 30
        row += 1

        info = [
            ("Home Team", match_info.get("home_team", "N/A")),
            ("Away Team", match_info.get("away_team", "N/A")),
            ("Competition", match_info.get("competition", "N/A")),
            ("Match Date", match_info.get("date", "N/A")),
            ("Venue", match_info.get("venue", "N/A")),
            ("Model Confidence", f"{pred.get('model_confidence', 0):.1%}"),
            ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]
        for label, value in info:
            _data_row(ws, row, [label, value])
            ws.cell(row=row, column=1).font = Font(bold=True)
            row += 1

        row += 1
        # Home Lineup
        home_lineup = match_info.get("home_lineup", [])
        if home_lineup:
            _header_row(ws, row, ["Home XI — #", "Name", "Position", "Goals (Season)", "xG/90"])
            row += 1
            for i, p in enumerate(home_lineup[:11]):
                _data_row(ws, row, [
                    p.get("jersey_no", ""),
                    p.get("name", ""),
                    p.get("position", ""),
                    p.get("goals_season", 0),
                    f"{p.get('xg_per90', 0):.2f}",
                ], alt=i % 2 == 1)
                row += 1

        row += 1
        # Away Lineup
        away_lineup = match_info.get("away_lineup", [])
        if away_lineup:
            _header_row(ws, row, ["Away XI — #", "Name", "Position", "Goals (Season)", "xG/90"])
            row += 1
            for i, p in enumerate(away_lineup[:11]):
                _data_row(ws, row, [
                    p.get("jersey_no", ""),
                    p.get("name", ""),
                    p.get("position", ""),
                    p.get("goals_season", 0),
                    f"{p.get('xg_per90', 0):.2f}",
                ], alt=i % 2 == 1)
                row += 1

        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 2: 1X2 & Double Chance
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_1x2_double_chance(self, wb, pred: Dict):
        ws = wb.create_sheet("1X2 & Double Chance")
        mr = pred.get("match_result", {})
        dc = pred.get("double_chance", {})

        _header_row(ws, 1, ["Market", "Outcome", "Probability", "Decimal Odds", "Fractional Odds"], freeze=True)
        rows = [
            ("1X2", "Home Win (1)", mr.get("home", 0)),
            ("1X2", "Draw (X)", mr.get("draw", 0)),
            ("1X2", "Away Win (2)", mr.get("away", 0)),
            ("Double Chance", "1X (Home or Draw)", dc.get("1X", 0)),
            ("Double Chance", "12 (Home or Away)", dc.get("12", 0)),
            ("Double Chance", "X2 (Draw or Away)", dc.get("X2", 0)),
        ]
        for i, (market, outcome, prob) in enumerate(rows, 2):
            decimal_odds = round(1 / prob, 2) if prob > 0 else "N/A"
            frac = self._to_fractional(prob)
            _pct_row(ws, i, [market, outcome, prob, decimal_odds, frac], alt=i % 2 == 0)
            _add_conditional_formatting(ws, "C", 2, len(rows) + 1)

        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 3: Goals Predictions
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_goals(self, wb, pred: Dict):
        ws = wb.create_sheet("Goals Predictions")
        btts = pred.get("btts", {})
        tg = pred.get("total_goals", {})
        ou = tg.get("over_under", {})

        _header_row(ws, 1, ["Market", "Outcome", "Probability", "Decimal Odds"])
        row = 2
        rows_data = [
            ("BTTS", "Yes", btts.get("yes", 0)),
            ("BTTS", "No", btts.get("no", 0)),
            ("Total Goals", f"Total (predicted: {tg.get('predicted', 0):.2f})", None),
            ("Home Goals", f"Predicted: {tg.get('home_predicted', 0):.2f}", None),
            ("Away Goals", f"Predicted: {tg.get('away_predicted', 0):.2f}", None),
        ]
        # Over/Under rows
        for key, val in ou.items():
            label = key.replace("_", ".").replace("over.", "Over ").replace("under.", "Under ")
            rows_data.append(("Over/Under", label, val))

        for i, (market, outcome, prob) in enumerate(rows_data):
            if prob is not None:
                odds = round(1 / prob, 2) if prob and prob > 0 else "N/A"
                _pct_row(ws, row, [market, outcome, prob, odds], alt=row % 2 == 0)
            else:
                _data_row(ws, row, [market, outcome, "—", "—"], alt=row % 2 == 0)
            row += 1

        _add_conditional_formatting(ws, "C", 2, row - 1)
        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 4: Score Predictions
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_correct_scores(self, wb, pred: Dict):
        ws = wb.create_sheet("Score Predictions")
        cs = pred.get("correct_scores", [])
        sd = pred.get("score_draw", {})

        _header_row(ws, 1, ["Rank", "Score", "Probability", "Decimal Odds", "Category"])
        for i, score in enumerate(cs[:20], 2):
            prob = score.get("probability", 0)
            h = score.get("home_goals", 0)
            a = score.get("away_goals", 0)
            cat = "Home Win" if h > a else ("Draw" if h == a else "Away Win")
            odds = round(1 / prob, 1) if prob > 0 else "N/A"
            _pct_row(ws, i, [i - 1, score.get("score"), prob, odds, cat], alt=i % 2 == 0)

        _add_conditional_formatting(ws, "C", 2, min(21, len(cs) + 1))

        row = len(cs[:20]) + 3
        _header_row(ws, row, ["Score Draw", "Probability", "Likely Scores"])
        row += 1
        _data_row(ws, row, [
            "Score Draw",
            sd.get("probability", 0),
            ", ".join(sd.get("likely_scores", [])),
        ])
        ws.cell(row=row, column=2).number_format = "0.00%"

        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 5: Special Markets
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_specials(self, wb, pred: Dict):
        ws = wb.create_sheet("Special Markets")
        eo = pred.get("total_even_odd", {})
        gbh = pred.get("goal_both_halves", {})
        gi = pred.get("goal_interval", {})

        row = 1
        _header_row(ws, row, ["Market", "Outcome", "Probability", "Decimal Odds"])
        row += 1
        specials = [
            ("Total Even/Odd", "Even", eo.get("even", 0)),
            ("Total Even/Odd", "Odd", eo.get("odd", 0)),
            ("Goal Both Halves", "Yes", gbh.get("yes", 0)),
            ("Goal Both Halves", "No", gbh.get("no", 0)),
        ]
        for i, (market, outcome, prob) in enumerate(specials, row):
            odds = round(1 / prob, 2) if prob > 0 else "N/A"
            _pct_row(ws, i, [market, outcome, prob, odds], alt=i % 2 == 0)
        row += len(specials) + 1

        # Goal intervals
        _header_row(ws, row, ["Goal Interval", "Probability", "Decimal Odds"])
        row += 1
        for i, (interval, prob) in enumerate(gi.items()):
            odds = round(1 / prob, 2) if prob > 0 else "N/A"
            _pct_row(ws, row, [interval, prob, odds], alt=i % 2 == 0)
            row += 1

        _add_conditional_formatting(ws, "B", 6, row - 1)
        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 6: Player Scorers
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_player_scorers(self, wb, pred: Dict):
        ws = wb.create_sheet("Player Scorers")
        players = pred.get("player_scorers", [])

        _header_row(ws, 1, [
            "Rank", "Name", "Team", "#", "Position",
            "Goals (Season)", "xG/90", "Score Probability", "Decimal Odds"
        ], freeze=True)

        for i, p in enumerate(players, 2):
            prob = p.get("probability", 0)
            odds = round(1 / prob, 2) if prob > 0 else "N/A"
            _pct_row(ws, i, [
                i - 1,
                p.get("name"),
                p.get("team", "").capitalize(),
                p.get("jersey_no", ""),
                p.get("position", ""),
                p.get("goals_season", 0),
                p.get("xg_per90", 0),
                prob,
                odds,
            ], alt=i % 2 == 0)

        if len(players) > 0:
            _add_conditional_formatting(ws, "H", 2, len(players) + 1)
        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sheet 7: Raw Features
    # ─────────────────────────────────────────────────────────────────────────────

    def _sheet_raw_features(self, wb, pred: Dict):
        ws = wb.create_sheet("Raw Feature Data")
        features = pred.get("features_used", {})

        _header_row(ws, 1, ["Feature Name", "Value", "Description"])
        descriptions = {
            "home_avg_goals_scored_5": "Home avg goals scored (last 5 matches)",
            "home_avg_goals_scored_10": "Home avg goals scored (last 10 matches)",
            "away_avg_goals_scored_5": "Away avg goals scored (last 5 matches)",
            "away_avg_goals_scored_10": "Away avg goals scored (last 10 matches)",
            "home_avg_goals_conceded_5": "Home avg goals conceded (last 5)",
            "away_avg_goals_conceded_5": "Away avg goals conceded (last 5)",
            "home_win_rate_10": "Home win rate (last 10 matches)",
            "away_win_rate_10": "Away win rate (last 10 matches)",
            "home_form_points": "Home form points (last 5)",
            "away_form_points": "Away form points (last 5)",
            "h2h_home_wins": "H2H home wins (last 5 meetings)",
            "h2h_draws": "H2H draws (last 5 meetings)",
            "h2h_away_wins": "H2H away wins (last 5 meetings)",
            "home_league_position": "Home team league position",
            "away_league_position": "Away team league position",
            "home_first_half_goals_avg": "Home avg 1st half goals (last 5)",
            "away_first_half_goals_avg": "Away avg 1st half goals (last 5)",
            "home_second_half_goals_avg": "Home avg 2nd half goals (last 5)",
            "away_second_half_goals_avg": "Away avg 2nd half goals (last 5)",
            "home_clean_sheet_rate": "Home clean sheet rate (last 5)",
            "away_clean_sheet_rate": "Away clean sheet rate (last 5)",
            "match_importance_weight": "Match importance multiplier",
            "home_avg_xg_per90": "Home avg xG per 90 (lineup)",
            "away_avg_xg_per90": "Away avg xG per 90 (lineup)",
        }

        for i, (feat, val) in enumerate(features.items(), 2):
            desc = descriptions.get(feat, "Engineered feature")
            _data_row(ws, i, [feat, round(float(val), 4) if isinstance(val, float) else val, desc], alt=i % 2 == 0)

        _autofit(ws)

    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_fractional(prob: float) -> str:
        if prob <= 0 or prob >= 1:
            return "N/A"
        decimal = 1 / prob
        numerator = decimal - 1
        # Simplify to reasonable fractional
        for denom in [1, 2, 4, 5, 8, 10, 20]:
            num = round(numerator * denom)
            if num > 0:
                return f"{num}/{denom}"
        return f"{round(numerator * 10)}/10"


# Singleton
excel_exporter = ExcelExporter()
