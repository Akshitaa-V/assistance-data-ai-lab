"""Rule-based baseline for case intake.

Generic keyword rules in English and German, written from the guidelines and
not from the test cases. It shows what a non-AI solution reaches on the same
test set, so an assistant has to beat it to be worth the effort. The summary is
extractive (the first 40 words of the message), so it cannot translate German
messages into English.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .evaluate import MAX_SUMMARY_WORDS, TestCase, load_test_cases

ABROAD = ["abroad", "holiday", "hotel", "flight", "ferry", "passport", "rental car",
          "italy", "austria", "spain", "france", "croatia", "greece", "turkey", "ausland", "urlaub"]
MEDICAL = ["hospital", "doctor", "doctors", "clinic", "ill", "sick", "collapsed", "broke", "fever",
           "injured", "injury", "fieber", "arzt", "krankenhaus"]

# Checked in order; the first match wins.
RULES = [
    ("Lockout", ["locked", "key", "keys", "schluessel"]),
    ("Towing", ["cannot be driven", "gearbox", "towed", "tow", "workshop", "accident", "collision", "unfall"]),
    ("Tyre", ["tyre", "tire", "puncture", "reifen", "losing air"]),
    ("Battery", ["battery", "batterie", "clicks", "klicken", "won't start", "will not start",
                 "springt nicht an", "lights were left on", "lights left on"]),
]

HIGH_URGENCY = ["motorway", "autobahn", "hard shoulder", "standstreifen", "tunnel", "country road",
                "child", "children", "kids", "kinder", "elderly", "mutter", "mother", "father", "dark", "dunkel"]
MOTORWAY_CODE = re.compile(r"\bA\s?\d{1,3}\b")


def _has(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def classify(text: str) -> str:
    t = text.lower()
    if _has(t, ABROAD):
        return "Medical Assistance Abroad" if _has(t, MEDICAL) else "Travel Assistance"
    for category, words in RULES:
        if _has(t, words):
            return category
    return "Breakdown"


def urgency(text: str, category: str) -> str:
    if category == "Medical Assistance Abroad":
        return "High"
    on_motorway = bool(MOTORWAY_CODE.search(text))
    return "High" if on_motorway or _has(text.lower(), HIGH_URGENCY) else "Normal"


def summarise(text: str) -> str:
    return " ".join(text.split()[:MAX_SUMMARY_WORDS])


def run(cases: list[TestCase] | None = None) -> list[dict[str, str]]:
    cases = cases or load_test_cases()
    answers = []
    for case in cases:
        category = classify(case.text)
        answers.append({
            "case_id": case.case_id,
            "category": category,
            "urgency": urgency(case.text, category),
            "summary": summarise(case.text),
        })
    return answers


def write_csv(path: Path, answers: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["case_id", "category", "urgency", "summary"])
        writer.writeheader()
        writer.writerows(answers)
    return path
