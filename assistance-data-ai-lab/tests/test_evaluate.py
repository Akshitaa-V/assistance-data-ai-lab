import pandas as pd
import pytest

from adl import baseline
from adl.evaluate import (
    CATEGORIES, build_batch_prompt, fact_coverage, is_english, load_test_cases, score,
    unsupported_facts, _place_gazetteer,
)


@pytest.fixture(scope="module")
def cases():
    return load_test_cases()


def perfect_answers(cases):
    return pd.DataFrame([{
        "case_id": c.case_id,
        "category": c.expected_category,
        "urgency": c.expected_urgency,
        "summary": " ".join(group[0] for group in c.required_facts),
    } for c in cases])


def test_test_set_is_valid(cases):
    assert len(cases) >= 25
    assert len({c.case_id for c in cases}) == len(cases)
    assert {c.expected_category for c in cases} == set(CATEGORIES)
    assert {c.expected_urgency for c in cases} == {"High", "Normal"}
    for c in cases:
        for group in c.required_facts:
            assert any(alt.lower() in c.text.lower() for alt in group), (c.case_id, group)


def test_perfect_answers_pass_the_gate(cases):
    metrics, _ = score(perfect_answers(cases), cases)
    assert metrics["category_accuracy"] == 1.0
    assert metrics["fact_coverage"] == 1.0
    assert metrics["passes_gate"]


def test_missing_an_urgent_case_fails_the_gate(cases):
    answers = perfect_answers(cases)
    first_high = answers.index[answers["urgency"] == "High"][0]
    answers.loc[first_high, "urgency"] = "Normal"
    metrics, _ = score(answers, cases)
    assert metrics["high_urgency_recall"] < 1.0
    assert "high_urgency_recall" in metrics["gate_failures"]


def test_unanswered_cases_count_as_wrong(cases):
    metrics, _ = score(perfect_answers(cases).iloc[:5], cases)
    assert metrics["answered"] == 5
    assert metrics["category_accuracy"] == pytest.approx(5 / len(cases))


def test_invented_facts_are_detected():
    places = _place_gazetteer()
    source = "Flat tyre on the A9 near Ingolstadt with two children."
    assert unsupported_facts("Flat tyre on A9 near Ingolstadt, two children.", source, places) == []
    assert unsupported_facts("Flat tyre on the A8 near Munich, 3 children.", source, places) == ["3", "A8", "Munich"]


def test_fact_coverage_and_language_checks():
    assert fact_coverage("Battery flat at home", [["batter"], ["home"]]) == 1.0
    assert fact_coverage("Battery flat", [["batter"], ["home"]]) == 0.5
    assert is_english("Member's car battery is flat, car is at home.")
    assert not is_english("Mein Auto springt nicht an, die Batterie ist leer.")


def test_baseline_is_scored_but_fails_on_german_summaries(cases):
    metrics, detail = score(pd.DataFrame(baseline.run(cases)), cases)
    assert metrics["category_accuracy"] >= 0.8
    assert metrics["passes_gate"] is False
    assert "english_summaries" in metrics["gate_failures"]


def test_prompt_contains_rules_and_every_case(cases):
    prompt = build_batch_prompt(cases)
    assert "case_id,category,urgency,summary" in prompt
    assert "test case" not in prompt.lower()
    for c in cases:
        assert f"{c.case_id}: {c.text}" in prompt
