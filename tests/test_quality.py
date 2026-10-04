import pandas as pd

from adl.generate import generate_clean
from adl.quality import RULES, run_checks


def test_every_injected_issue_is_caught_exactly(generated, quality):
    q = quality.quarantine
    for rule, case_ids in generated.injected.items():
        flagged = set(q.loc[q["dq_reason"].str.contains(rule), "case_id"])
        assert flagged == case_ids, rule


def test_no_false_positives_on_clean_data():
    clean = generate_clean(n_cases=3_000, seed=7)
    result = run_checks(clean)
    assert result.quarantine.empty
    assert len(result.clean) == len(clean)


def test_rows_are_kept_or_quarantined_never_lost(generated, quality):
    assert len(quality.clean) + len(quality.quarantine) == len(generated.cases)
    assert quality.clean["case_id"].is_unique


def test_quarantine_lists_every_failed_rule():
    df = generate_clean(n_cases=10, seed=1)
    df.loc[0, "region"] = None
    df.loc[0, "csat"] = 9.0
    result = run_checks(df)
    assert result.quarantine.loc[0, "dq_reason"] == "missing_region;csat_out_of_range"


def test_summary_has_one_row_per_rule(quality):
    assert list(quality.summary["rule"]) == list(RULES)
    assert isinstance(quality.summary, pd.DataFrame)
