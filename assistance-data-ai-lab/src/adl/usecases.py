"""Scoring and ranking of Data & AI use cases.

Each candidate is rated 1-5 on value, effort, data readiness and risk (privacy,
safety, wrong answers reaching members). The score rewards value and ready
data and penalises effort and risk. High-risk use cases are never ranked as
quick wins: they need a data protection review first, whatever their score.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
USE_CASES = ROOT / "data" / "use_cases.csv"

RATING_COLUMNS = ["value", "effort", "data_ready", "risk"]
HIGH_RISK = 5


def load(path: Path = USE_CASES) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in RATING_COLUMNS:
        if not df[col].between(1, 5).all():
            raise ValueError(f"Column {col} must be rated 1-5")
    return df


def priority_score(row: pd.Series) -> float:
    return 2 * row["value"] + row["data_ready"] - row["effort"] - row["risk"]


def quadrant(row: pd.Series) -> str:
    if row["risk"] >= HIGH_RISK:
        return "Review first"
    if row["value"] >= 4 and row["effort"] <= 2:
        return "Quick win"
    if row["value"] >= 4:
        return "Strategic project"
    if row["effort"] <= 2:
        return "Small improvement"
    return "Later"


ORDER = {"Quick win": 0, "Strategic project": 1, "Small improvement": 2, "Later": 3, "Review first": 4}


def rank(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = load() if df is None else df.copy()
    df["score"] = df.apply(priority_score, axis=1)
    df["recommendation"] = df.apply(quadrant, axis=1)
    df["_order"] = df["recommendation"].map(ORDER)
    df = df.sort_values(["_order", "score", "id"], ascending=[True, False, True]).drop(columns="_order")
    df.insert(0, "rank", range(1, len(df) + 1))
    return df.reset_index(drop=True)
