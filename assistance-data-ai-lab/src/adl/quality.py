"""Data quality rules for the case table.

Rows that break a rule are not dropped silently. They go to a quarantine table
with every reason they failed, so a data owner can fix the source and the
numbers in the report stay explainable.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .generate import DATA_END, REGIONS, SERVICE_TYPES

MAX_PLAUSIBLE_ARRIVAL_MIN = 480  # 8 hours; longer waits are data entry errors

# rule name -> (description, function that returns True for BAD rows)
RULES = {
    "duplicate_case_id": (
        "The same case id appears more than once; the first row is kept.",
        lambda d: d.duplicated("case_id", keep="first"),
    ),
    "missing_region": (
        "Region is empty, so the case cannot be assigned to a regional team.",
        lambda d: d["region"].isna() | ~d["region"].isin(REGIONS.keys()),
    ),
    "unknown_service_type": (
        "Service type is not in the service catalogue.",
        lambda d: ~d["service_type"].isin(SERVICE_TYPES),
    ),
    "negative_time": (
        "First contact or arrival time is below zero.",
        lambda d: (d["first_contact_min"] < 0) | (d["arrival_min"] < 0),
    ),
    "implausible_arrival": (
        f"Arrival time above {MAX_PLAUSIBLE_ARRIVAL_MIN} minutes.",
        lambda d: d["arrival_min"] > MAX_PLAUSIBLE_ARRIVAL_MIN,
    ),
    "future_timestamp": (
        "Case is dated after the end of the reporting period.",
        lambda d: pd.to_datetime(d["created_at"]) > DATA_END,
    ),
    "csat_out_of_range": (
        "Satisfaction score outside the 1-5 scale.",
        lambda d: d["csat"].notna() & ~d["csat"].between(1, 5),
    ),
}


@dataclass
class QualityResult:
    clean: pd.DataFrame
    quarantine: pd.DataFrame
    summary: pd.DataFrame  # one row per rule with the number of rows it flagged


def run_checks(df: pd.DataFrame) -> QualityResult:
    flags = pd.DataFrame({name: fn(df).fillna(False).astype(bool) for name, (_, fn) in RULES.items()})
    bad = flags.any(axis=1)

    reasons = flags.apply(lambda row: ";".join(name for name, hit in row.items() if hit), axis=1)
    quarantine = df.loc[bad].copy()
    quarantine.insert(0, "dq_reason", reasons[bad])

    summary = pd.DataFrame({
        "rule": list(RULES),
        "description": [desc for desc, _ in RULES.values()],
        "rows_flagged": [int(flags[name].sum()) for name in RULES],
    })
    clean = df.loc[~bad].reset_index(drop=True)
    return QualityResult(clean=clean, quarantine=quarantine.reset_index(drop=True), summary=summary)
