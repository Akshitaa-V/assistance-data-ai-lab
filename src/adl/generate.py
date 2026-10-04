"""Synthetic case data for a fictional mobility assistance service.

The data is made up but follows patterns a real assistance desk would see:
battery cases peak in winter, travel and medical assistance abroad peak in
summer, arrival times are longer in winter and in rural areas, and the share of
cases reported through the app grows after a digital intake launch in July.

Known data quality problems are injected on purpose, and every injected row is
logged, so the quality checks can be tested against a ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SEED = 42
YEAR = 2025
DATA_END = pd.Timestamp(f"{YEAR}-12-31 23:59:59")
DIGITAL_INTAKE_LAUNCH = pd.Timestamp(f"{YEAR}-07-01")

REGIONS = {
    # region: (share of cases, rural factor that slows arrival)
    "Bavaria": (0.22, 1.15),
    "Baden-Wuerttemberg": (0.16, 1.05),
    "North Rhine-Westphalia": (0.20, 0.95),
    "Hesse": (0.09, 1.00),
    "Lower Saxony": (0.11, 1.12),
    "Saxony": (0.07, 1.10),
    "Berlin": (0.08, 0.85),
    "Hamburg": (0.07, 0.85),
}

# Services handled on the road have an arrival time and an on-site result.
ROAD_SERVICES = ["Breakdown", "Battery", "Tyre", "Towing", "Lockout"]
REMOTE_SERVICES = ["Medical Assistance Abroad", "Travel Assistance"]
SERVICE_TYPES = ROAD_SERVICES + REMOTE_SERVICES

# Base monthly weight per service (Jan..Dec) to create seasonality.
SEASONALITY = {
    "Breakdown": [1.0, 1.0, 0.9, 0.9, 0.9, 1.0, 1.2, 1.2, 1.0, 0.9, 1.0, 1.1],
    "Battery": [2.2, 2.0, 1.3, 0.8, 0.6, 0.5, 0.5, 0.5, 0.6, 0.9, 1.4, 2.1],
    "Tyre": [0.9, 0.8, 1.3, 1.5, 1.0, 0.8, 0.9, 0.9, 0.9, 1.4, 1.3, 1.0],
    "Towing": [1.2, 1.1, 1.0, 0.9, 0.9, 1.0, 1.1, 1.1, 1.0, 0.9, 1.0, 1.2],
    "Lockout": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.1, 1.0, 1.0, 1.0, 1.0],
    "Medical Assistance Abroad": [0.4, 0.4, 0.5, 0.8, 1.0, 1.5, 2.2, 2.4, 1.3, 0.7, 0.4, 0.6],
    "Travel Assistance": [0.5, 0.5, 0.6, 0.9, 1.0, 1.5, 2.1, 2.3, 1.2, 0.7, 0.5, 0.7],
}
SERVICE_BASE_SHARE = {
    "Breakdown": 0.30, "Battery": 0.20, "Tyre": 0.13, "Towing": 0.12,
    "Lockout": 0.07, "Medical Assistance Abroad": 0.08, "Travel Assistance": 0.10,
}

VEHICLES = ["Car", "Electric car", "Camper van", "Motorcycle"]
VEHICLE_P = [0.72, 0.14, 0.08, 0.06]

PLACES = [
    "on the A9 near Ingolstadt", "on the A3 near Passau", "in a supermarket car park",
    "at home in the driveway", "on a country road outside the village",
    "at a motorway service station", "in an underground car park", "at the office car park",
]
UNSAFE_PLACES = {"on the A9 near Ingolstadt", "on the A3 near Passau", "on a country road outside the village"}

ISSUE_TEMPLATES = {
    "Breakdown": [
        "Engine stopped while driving, warning light came on, now standing {place}.",
        "{vehicle} lost power and will not restart, I am {place}.",
        "Strange noise from the engine and then it died {place}.",
    ],
    "Battery": [
        "{vehicle} will not start this morning, battery seems dead, {place}.",
        "Lights left on overnight, battery flat, {place}.",
        "Starter only clicks, probably the battery, {place}.",
    ],
    "Tyre": [
        "Flat tyre on the front left, {place}, no spare wheel.",
        "Tyre pressure warning and the tyre is losing air {place}.",
        "Puncture after driving over debris {place}.",
    ],
    "Towing": [
        "Accident damage, {vehicle} cannot be driven any more, needs to be towed from {place}.",
        "Gearbox broken, car must go to a workshop, standing {place}.",
    ],
    "Lockout": [
        "Keys locked inside the {vehicle}, standing {place}.",
        "Lost the car key, cannot open the {vehicle}, {place}.",
    ],
    "Medical Assistance Abroad": [
        "Member fell ill on holiday in Italy and needs a German-speaking doctor.",
        "Broken leg after a hiking accident in Austria, asking about transport home.",
        "Member in hospital in Spain, family asks for help with the costs.",
    ],
    "Travel Assistance": [
        "Car broke down in France, member needs a hotel and a rental car to continue.",
        "Lost passport and wallet in Croatia, needs help with documents.",
        "Ferry cancelled, member asks for alternative travel to Greece.",
    ],
}
URGENCY_CUES = ["Children in the car.", "It is getting dark.", "Member is elderly.", ""]


@dataclass
class GeneratedData:
    cases: pd.DataFrame
    injected: dict[str, set[str]] = field(default_factory=dict)


def _issue_text(rng: np.random.Generator, service: str, vehicle: str, place: str) -> str:
    template = ISSUE_TEMPLATES[service][rng.integers(len(ISSUE_TEMPLATES[service]))]
    text = template.format(vehicle=vehicle.lower() if service in ("Lockout",) else vehicle, place=place)
    cue = URGENCY_CUES[rng.integers(len(URGENCY_CUES))] if service in ROAD_SERVICES else ""
    return (text + " " + cue).strip()


def generate_clean(n_cases: int = 24_000, seed: int = SEED) -> pd.DataFrame:
    """Generate the clean case table (before any data quality issues)."""
    rng = np.random.default_rng(seed)

    # Days of the year, weighted by total seasonal demand.
    days = pd.date_range(f"{YEAR}-01-01", f"{YEAR}-12-31", freq="D")
    month_idx = days.month.values - 1
    day_weight = np.zeros(len(days))
    for service, share in SERVICE_BASE_SHARE.items():
        day_weight += share * np.array(SEASONALITY[service])[month_idx]
    day_weight /= day_weight.sum()

    day_pick = rng.choice(len(days), size=n_cases, p=day_weight)
    created = days[day_pick] + pd.to_timedelta(rng.integers(0, 24 * 60, size=n_cases), unit="m")
    months = created.month.values - 1

    # Service type depends on the month.
    services = np.empty(n_cases, dtype=object)
    names = list(SERVICE_BASE_SHARE)
    base = np.array([SERVICE_BASE_SHARE[s] for s in names])
    for m in range(12):
        mask = months == m
        p = base * np.array([SEASONALITY[s][m] for s in names])
        services[mask] = rng.choice(names, size=mask.sum(), p=p / p.sum())

    region_names = list(REGIONS)
    region_p = np.array([REGIONS[r][0] for r in region_names])
    regions = rng.choice(region_names, size=n_cases, p=region_p / region_p.sum())
    vehicles = rng.choice(VEHICLES, size=n_cases, p=VEHICLE_P)

    # Channel: app share grows after the digital intake launch.
    after_launch = created >= DIGITAL_INTAKE_LAUNCH
    p_app = np.where(after_launch, 0.34, 0.17)
    p_web = np.full(n_cases, 0.06)
    u = rng.random(n_cases)
    channel = np.where(u < p_app, "App", np.where(u < p_app + p_web, "Web", "Phone"))

    # Minutes until a dispatcher confirms the case.
    first_contact = rng.gamma(2.0, 1.6, size=n_cases)
    first_contact = np.where(channel == "App", first_contact * np.where(after_launch, 0.6, 1.4), first_contact)
    first_contact = np.round(first_contact + 0.5, 1)

    # Arrival time for road services: slower in winter and in rural regions.
    winter = np.isin(months, [0, 1, 11])
    rural = np.array([REGIONS[r][1] for r in regions])
    arrival = rng.gamma(4.0, 11.0, size=n_cases) * rural * np.where(winter, 1.25, 1.0)
    is_road = np.isin(services, ROAD_SERVICES)
    arrival = np.where(is_road, np.round(arrival + 10), np.nan)

    # On-site resolution: towing is never solved on site; battery and lockout usually are.
    p_fix = pd.Series(services).map(
        {"Breakdown": 0.62, "Battery": 0.90, "Tyre": 0.80, "Towing": 0.0, "Lockout": 0.93}
    ).to_numpy(dtype=float)
    resolved = np.where(is_road, (rng.random(n_cases) < np.nan_to_num(p_fix)).astype(float), np.nan)

    # Satisfaction (1-5); about 40% of members skip the survey. Long waits hurt the score.
    wait = np.nan_to_num(arrival, nan=40.0)
    csat_mean = 4.6 - np.clip((wait - 45) / 60, 0, 1.6) + np.where(resolved == 1, 0.2, 0.0)
    csat = np.clip(np.round(rng.normal(csat_mean, 0.6)), 1, 5)
    csat = np.where(rng.random(n_cases) < 0.40, np.nan, csat)

    places = rng.choice(PLACES, size=n_cases)
    issue = [_issue_text(rng, s, v, p) for s, v, p in zip(services, vehicles, places)]

    df = pd.DataFrame({
        "case_id": [f"C{idx:06d}" for idx in range(1, n_cases + 1)],
        "created_at": created,
        "region": regions,
        "service_type": services,
        "channel": channel,
        "vehicle_type": vehicles,
        "issue_text": issue,
        "first_contact_min": first_contact,
        "arrival_min": arrival,
        "resolved_on_site": resolved,
        "csat": csat,
    })
    return df.sort_values("created_at").reset_index(drop=True)


def inject_quality_issues(df: pd.DataFrame, seed: int = SEED) -> GeneratedData:
    """Add known data quality problems and log which case ids carry each one."""
    rng = np.random.default_rng(seed + 1)
    df = df.copy()
    injected: dict[str, set[str]] = {}
    used: set[int] = set()

    def pick(n: int, mask: np.ndarray | None = None) -> np.ndarray:
        pool = np.arange(len(df)) if mask is None else np.flatnonzero(mask)
        pool = np.array([i for i in pool if i not in used])
        chosen = rng.choice(pool, size=n, replace=False)
        used.update(chosen.tolist())
        return chosen

    road = df["service_type"].isin(ROAD_SERVICES).to_numpy()

    idx = pick(150)
    df.loc[idx, "region"] = None
    injected["missing_region"] = set(df.loc[idx, "case_id"])

    idx = pick(60)
    df.loc[idx, "service_type"] = rng.choice(["Batery", "Breakdwon", "tyre ", "n/a"], size=len(idx))
    injected["unknown_service_type"] = set(df.loc[idx, "case_id"])

    idx = pick(80, road)
    df.loc[idx, "arrival_min"] = -df.loc[idx, "arrival_min"]
    injected["negative_time"] = set(df.loc[idx, "case_id"])

    idx = pick(40, road)
    df.loc[idx, "arrival_min"] = rng.integers(700, 3000, size=len(idx)).astype(float)
    injected["implausible_arrival"] = set(df.loc[idx, "case_id"])

    idx = pick(30)
    df.loc[idx, "created_at"] = DATA_END + pd.to_timedelta(rng.integers(1, 200, size=len(idx)), unit="D")
    injected["future_timestamp"] = set(df.loc[idx, "case_id"])

    idx = pick(50)
    df.loc[idx, "csat"] = rng.choice([0.0, 6.0, 10.0], size=len(idx))
    injected["csat_out_of_range"] = set(df.loc[idx, "case_id"])

    # Duplicates: the same case exported twice. Picked from rows without other issues.
    idx = pick(300)
    dupes = df.loc[idx].copy()
    injected["duplicate_case_id"] = set(dupes["case_id"])
    df = pd.concat([df, dupes], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    return GeneratedData(cases=df, injected=injected)


def generate(n_cases: int = 24_000, seed: int = SEED) -> GeneratedData:
    return inject_quality_issues(generate_clean(n_cases, seed), seed)
