"""Evaluate an AI assistant's case intake answers against fixed test cases.

The idea: before an assistant such as Microsoft 365 Copilot is used in a real
process, write down what a correct answer looks like (evaluation/guidelines.md
and evaluation/test_cases.jsonl), collect the assistant's answers, and score
them the same way every time. A rule-based baseline is scored on the same test
set so there is always a reference point.

Answers are read from a CSV with the columns case_id, category, urgency, summary.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TEST_CASES = ROOT / "evaluation" / "test_cases.jsonl"
GUIDELINES = ROOT / "evaluation" / "guidelines.md"

CATEGORIES = [
    "Battery", "Tyre", "Lockout", "Towing", "Breakdown",
    "Medical Assistance Abroad", "Travel Assistance",
]
URGENCIES = ["High", "Normal"]
MAX_SUMMARY_WORDS = 40

# Release gate: what an assistant must reach before it is used with real cases.
GATE = {
    "category_accuracy": 0.90,
    "high_urgency_recall": 1.00,  # missing an urgent case is never acceptable
    "fact_coverage": 0.90,
    "english_summaries": 1.00,  # dispatchers get every handover in English
    "unsupported_fact_cases": 0,
}

ROAD_CODE = re.compile(r"\b[AB]\s?\d{1,3}\b")
NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")


@dataclass
class TestCase:
    case_id: str
    text: str
    expected_category: str
    expected_urgency: str
    required_facts: list[list[str]]


def load_test_cases(path: Path = TEST_CASES) -> list[TestCase]:
    with path.open(encoding="utf-8") as fh:
        return [TestCase(**json.loads(line)) for line in fh if line.strip()]


def load_responses(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = {"case_id", "category", "urgency", "summary"} - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    for col in ("case_id", "category", "urgency", "summary"):
        df[col] = df[col].str.strip()
    return df.drop_duplicates("case_id", keep="first")


PLACES_FILE = ROOT / "evaluation" / "places.txt"


def _place_gazetteer(path: Path = PLACES_FILE) -> set[str]:
    """Known place names; one in a summary but not in the message counts as invented."""
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def unsupported_facts(summary: str, source: str, gazetteer: set[str]) -> list[str]:
    """Numbers, road codes and known place names in the summary that are not in the source."""
    found: list[str] = []
    src = source.lower()
    for code in ROAD_CODE.findall(summary):
        if code.replace(" ", "").lower() not in src.replace(" ", ""):
            found.append(code)
    without_codes = ROAD_CODE.sub(" ", summary)
    for num in NUMBER.findall(without_codes):
        if not re.search(rf"\b{re.escape(num)}\b", source):
            found.append(num)
    for place in gazetteer:
        if re.search(rf"\b{re.escape(place)}\b", summary) and place.lower() not in src:
            found.append(place)
    return sorted(set(found))


GERMAN_MARKERS = {"der", "die", "das", "ich", "und", "nicht", "wir", "auf", "ist", "mein", "meine",
                  "dem", "ein", "eine", "seit", "zu", "an", "kennt", "keinen", "stehe", "haben"}


def is_english(summary: str) -> bool:
    """Rough check: a summary with two or more common German words is not English."""
    words = re.findall(r"[a-zäöüß]+", summary.lower())
    return sum(word in GERMAN_MARKERS for word in words) < 2


def fact_coverage(summary: str, required: list[list[str]]) -> float:
    if not required:
        return 1.0
    text = summary.lower()
    hits = sum(any(alt.lower() in text for alt in group) for group in required)
    return hits / len(required)


def score(responses: pd.DataFrame, cases: list[TestCase] | None = None) -> tuple[dict, pd.DataFrame]:
    cases = cases or load_test_cases()
    gazetteer = _place_gazetteer()
    by_id = responses.set_index("case_id").to_dict("index")

    rows = []
    for case in cases:
        answer = by_id.get(case.case_id, {"category": "", "urgency": "", "summary": ""})
        summary = answer["summary"]
        words = len(summary.split())
        unsupported = unsupported_facts(summary, case.text, gazetteer)
        rows.append({
            "case_id": case.case_id,
            "answered": case.case_id in by_id,
            "expected_category": case.expected_category,
            "category": answer["category"],
            "category_ok": answer["category"].lower() == case.expected_category.lower(),
            "expected_urgency": case.expected_urgency,
            "urgency": answer["urgency"],
            "urgency_ok": answer["urgency"].lower() == case.expected_urgency.lower(),
            "fact_coverage": fact_coverage(summary, case.required_facts),
            "summary_words": words,
            "within_word_limit": 0 < words <= MAX_SUMMARY_WORDS,
            "english": bool(summary) and is_english(summary),
            "unsupported_facts": ", ".join(unsupported),
        })
    detail = pd.DataFrame(rows)

    high = detail[detail["expected_urgency"] == "High"]
    metrics = {
        "test_cases": len(detail),
        "answered": int(detail["answered"].sum()),
        "category_accuracy": float(detail["category_ok"].mean()),
        "urgency_accuracy": float(detail["urgency_ok"].mean()),
        "high_urgency_recall": float(high["urgency_ok"].mean()) if len(high) else 1.0,
        "fact_coverage": float(detail["fact_coverage"].mean()),
        "within_word_limit": float(detail["within_word_limit"].mean()),
        "english_summaries": float(detail["english"].mean()),
        "unsupported_fact_cases": int((detail["unsupported_facts"] != "").sum()),
    }
    metrics["gate_failures"] = [
        name for name, ok in (
            ("category_accuracy", metrics["category_accuracy"] >= GATE["category_accuracy"]),
            ("high_urgency_recall", metrics["high_urgency_recall"] >= GATE["high_urgency_recall"]),
            ("fact_coverage", metrics["fact_coverage"] >= GATE["fact_coverage"]),
            ("english_summaries", metrics["english_summaries"] >= GATE["english_summaries"]),
            ("unsupported_fact_cases", metrics["unsupported_fact_cases"] <= GATE["unsupported_fact_cases"]),
        ) if not ok
    ]
    metrics["passes_gate"] = not metrics["gate_failures"]
    return metrics, detail


def write_response_template(path: Path, cases: list[TestCase] | None = None) -> Path:
    """Empty CSV with one row per test case, ready to fill with an assistant's answers."""
    cases = cases or load_test_cases()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["case_id", "category", "urgency", "summary"])
        for case in cases:
            writer.writerow([case.case_id, "", "", ""])
    return path


def build_batch_prompt(cases: list[TestCase] | None = None) -> str:
    """One prompt that can be pasted into Microsoft Copilot (or any chat assistant)."""
    cases = cases or load_test_cases()
    text = GUIDELINES.read_text(encoding="utf-8")
    guidelines = text[text.index("## Category"):].strip()  # rules only, without the intro
    lines = [
        "You support the dispatchers of a roadside and travel assistance service.",
        "Classify each incoming member message and write a short handover summary.",
        "Follow these guidelines exactly:",
        "",
        guidelines,
        "",
        "Answer ONLY with CSV, no explanations, using this header:",
        "case_id,category,urgency,summary",
        "Put the summary in double quotes. Use the category names exactly as written above.",
        "",
        "Messages:",
    ]
    for case in cases:
        lines.append(f"{case.case_id}: {case.text}")
    return "\n".join(lines) + "\n"
