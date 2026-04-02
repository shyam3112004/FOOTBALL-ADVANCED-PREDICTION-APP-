from scipy.stats import poisson
import numpy as np
from typing import List, Dict, Any
from config import MAX_CORRECT_SCORE


def build_correct_score_grid(home_lambda: float, away_lambda: float) -> List[Dict]:
    """
    Build full score probability grid using Poisson distribution.
    Returns list of {home_goals, away_goals, score, probability} dicts.
    """
    home_lambda = max(0.1, float(home_lambda))
    away_lambda = max(0.1, float(away_lambda))

    grid = []
    for h in range(MAX_CORRECT_SCORE + 1):
        for a in range(MAX_CORRECT_SCORE + 1):
            prob = float(poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda))
            grid.append({
                "home_goals": h,
                "away_goals": a,
                "score": f"{h}-{a}",
                "probability": prob,
            })

    # Normalize
    total = sum(g["probability"] for g in grid)
    if total > 0:
        for g in grid:
            g["probability"] = round(g["probability"] / total, 6)

    grid.sort(key=lambda x: x["probability"], reverse=True)
    return grid


def score_draw_probability(correct_scores: List[Dict]) -> Dict[str, Any]:
    """Extract score draw probability (1-1, 2-2, etc.) from correct score grid."""
    draw_scores = [
        s for s in correct_scores
        if s["home_goals"] == s["away_goals"] and s["home_goals"] >= 1
    ]
    prob = sum(s["probability"] for s in draw_scores)
    return {
        "probability": round(float(prob), 4),
        "likely_scores": [s["score"] for s in draw_scores[:3]],
    }


def even_odd_probability(correct_scores: List[Dict]) -> Dict[str, float]:
    """Calculate probability of even vs odd total goals."""
    even = sum(
        s["probability"] for s in correct_scores
        if (s["home_goals"] + s["away_goals"]) % 2 == 0
    )
    odd = sum(
        s["probability"] for s in correct_scores
        if (s["home_goals"] + s["away_goals"]) % 2 == 1
    )
    total = even + odd or 1.0
    return {
        "even": round(float(even / total), 4),
        "odd": round(float(odd / total), 4),
    }


def over_under_probabilities(total_lambda: float) -> Dict[str, float]:
    """Generate over/under threshold probabilities."""
    thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
    result = {}
    for t in thresholds:
        k_val = int(t + 0.5)
        under = float(sum(poisson.pmf(k, total_lambda) for k in range(k_val + 1)))
        under = float(np.clip(under, 0.01, 0.99))
        key = str(t).replace(".", "_")
        result[f"over_{key}"] = round(1.0 - under, 4)
        result[f"under_{key}"] = round(under, 4)
    return result
