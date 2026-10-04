"""KPI library.

Every KPI is defined once: name, business question, owner, formula, the SQL in
sql/kpis.sql and the DAX measure in powerbi/DAX_MEASURES.md. The tests check
that the pandas and SQL versions give the same number, and that every KPI has
its SQL and DAX written down.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .model import SLA_ARRIVAL_MIN, StarSchema

ROOT = Path(__file__).resolve().parents[2]
SQL_FILE = ROOT / "sql" / "kpis.sql"
DAX_FILE = ROOT / "powerbi" / "DAX_MEASURES.md"


@dataclass(frozen=True)
class KPI:
    key: str
    name: str
    question: str
    owner: str
    formula: str
    unit: str  # "count", "pct", "min", "score"


KPIS = [
    KPI("case_volume", "Case volume", "How many assistance cases did we handle?",
        "Operations Planning", "COUNT(cases)", "count"),
    KPI("sla_compliance_rate", "SLA compliance", f"Did help arrive within {SLA_ARRIVAL_MIN} minutes?",
        "Road Service Operations", f"road cases with arrival <= {SLA_ARRIVAL_MIN} min / road cases", "pct"),
    KPI("median_arrival_min", "Median arrival time", "How long does a typical member wait on the road?",
        "Road Service Operations", "MEDIAN(arrival_min) over road cases", "min"),
    KPI("on_site_resolution_rate", "On-site resolution", "How often is the problem fixed without towing?",
        "Road Service Operations", "road cases resolved on site / road cases", "pct"),
    KPI("avg_first_contact_min", "Avg. time to first contact", "How fast does a dispatcher confirm a case?",
        "Contact Centre", "AVERAGE(first_contact_min)", "min"),
    KPI("csat_avg", "Member satisfaction (CSAT)", "How satisfied are members who answer the survey?",
        "Member Experience", "AVERAGE(csat) over answered surveys", "score"),
    KPI("survey_response_rate", "Survey response rate", "How many members answer the survey?",
        "Member Experience", "cases with csat / cases", "pct"),
    KPI("app_share", "App channel share", "How many cases come in digitally through the app?",
        "Digital Products", "cases via App / cases", "pct"),
]
KPI_BY_KEY = {k.key: k for k in KPIS}


def _joined(star: StarSchema) -> pd.DataFrame:
    return (star.fact_case
            .merge(star.dim_date[["date_key", "month", "month_name", "season"]], on="date_key")
            .merge(star.dim_region, on="region_key")
            .merge(star.dim_service, on="service_key")
            .merge(star.dim_channel, on="channel_key"))


def _kpis_for(frame: pd.DataFrame) -> dict[str, float]:
    road = frame[frame["service_group"] == "Road"]
    return {
        "case_volume": float(len(frame)),
        "sla_compliance_rate": float(road["sla_met"].mean()),
        "median_arrival_min": float(road["arrival_min"].median()),
        "on_site_resolution_rate": float(road["resolved_on_site"].mean()),
        "avg_first_contact_min": float(frame["first_contact_min"].mean()),
        "csat_avg": float(frame["csat"].mean()),
        "survey_response_rate": float(frame["csat"].notna().mean()),
        "app_share": float((frame["channel"] == "App").mean()),
    }


def compute_kpis(star: StarSchema) -> dict[str, float]:
    return _kpis_for(_joined(star))


def kpis_by(star: StarSchema, column: str) -> pd.DataFrame:
    """KPIs per value of a column, e.g. month, region or service_type."""
    joined = _joined(star)
    rows = []
    for value, group in joined.groupby(column, sort=True):
        rows.append({column: value, **_kpis_for(group)})
    return pd.DataFrame(rows)


def load_sql_queries(path: Path = SQL_FILE) -> dict[str, str]:
    """Read queries written as '-- name: <kpi_key>' blocks."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.MULTILINE)
    return {blocks[i]: blocks[i + 1].strip() for i in range(1, len(blocks), 2)}


def to_sqlite(star: StarSchema) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    for name, table in star.tables().items():
        out = table.copy()
        for col in out.columns:
            if pd.api.types.is_datetime64_any_dtype(out[col]):
                out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            elif str(out[col].dtype) == "Int64":
                out[col] = out[col].astype(object).where(out[col].notna(), None)
        out.to_sql(name, con, index=False)
    return con


def compute_kpis_sql(star: StarSchema) -> dict[str, float]:
    con = to_sqlite(star)
    try:
        return {key: float(con.execute(sql).fetchone()[0]) for key, sql in load_sql_queries().items()}
    finally:
        con.close()


def format_value(key: str, value: float) -> str:
    unit = KPI_BY_KEY[key].unit
    if unit == "count":
        return f"{value:,.0f}"
    if unit == "pct":
        return f"{value:.1%}"
    if unit == "min":
        return f"{value:.1f} min"
    return f"{value:.2f} / 5"
