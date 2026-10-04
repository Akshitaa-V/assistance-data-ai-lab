"""Star schema for Power BI: one fact table and four dimensions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .generate import ROAD_SERVICES

SLA_ARRIVAL_MIN = 60  # target: help on site within 60 minutes


def _season(month: int) -> str:
    return {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
            6: "Summer", 7: "Summer", 8: "Summer"}.get(month, "Autumn")


@dataclass
class StarSchema:
    fact_case: pd.DataFrame
    dim_date: pd.DataFrame
    dim_region: pd.DataFrame
    dim_service: pd.DataFrame
    dim_channel: pd.DataFrame

    def tables(self) -> dict[str, pd.DataFrame]:
        return {
            "fact_case": self.fact_case,
            "dim_date": self.dim_date,
            "dim_region": self.dim_region,
            "dim_service": self.dim_service,
            "dim_channel": self.dim_channel,
        }

    def to_csv(self, folder: Path) -> list[Path]:
        folder.mkdir(parents=True, exist_ok=True)
        paths = []
        for name, table in self.tables().items():
            path = folder / f"{name}.csv"
            table.to_csv(path, index=False)
            paths.append(path)
        return paths


def build_star_schema(clean: pd.DataFrame) -> StarSchema:
    df = clean.copy()
    df["created_at"] = pd.to_datetime(df["created_at"])

    dates = pd.date_range(df["created_at"].min().normalize(), df["created_at"].max().normalize(), freq="D")
    dim_date = pd.DataFrame({"date": dates})
    dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["quarter"] = "Q" + dim_date["date"].dt.quarter.astype(str)
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
    dim_date["weekday"] = dim_date["date"].dt.strftime("%a")
    dim_date["is_weekend"] = dim_date["date"].dt.weekday >= 5
    dim_date["season"] = dim_date["month"].map(_season)
    dim_date = dim_date[["date_key", "date", "year", "quarter", "month", "month_name", "weekday", "is_weekend", "season"]]

    def dim(values: pd.Series, key: str, col: str) -> pd.DataFrame:
        out = pd.DataFrame({col: sorted(values.dropna().unique())})
        out.insert(0, key, range(1, len(out) + 1))
        return out

    dim_region = dim(df["region"], "region_key", "region")
    dim_service = dim(df["service_type"], "service_key", "service_type")
    dim_service["service_group"] = dim_service["service_type"].map(
        lambda s: "Road" if s in ROAD_SERVICES else "Remote"
    )
    dim_channel = dim(df["channel"], "channel_key", "channel")

    fact = df.merge(dim_region, on="region").merge(dim_service, on="service_type").merge(dim_channel, on="channel")
    fact["date_key"] = fact["created_at"].dt.strftime("%Y%m%d").astype(int)
    is_road = fact["service_group"] == "Road"
    fact["sla_met"] = pd.Series(pd.NA, index=fact.index, dtype="Int64")
    fact.loc[is_road, "sla_met"] = (fact.loc[is_road, "arrival_min"] <= SLA_ARRIVAL_MIN).astype(int)
    fact["resolved_on_site"] = fact["resolved_on_site"].astype("Int64")
    fact = fact[[
        "case_id", "created_at", "date_key", "region_key", "service_key", "channel_key", "vehicle_type",
        "issue_text", "first_contact_min", "arrival_min", "sla_met", "resolved_on_site", "csat",
    ]].sort_values("created_at").reset_index(drop=True)

    return StarSchema(fact, dim_date, dim_region, dim_service, dim_channel)
