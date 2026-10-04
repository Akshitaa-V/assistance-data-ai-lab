import pandas as pd
import pytest

from adl.usecases import load, rank


def test_backlog_is_ranked_with_unique_ranks():
    ranked = rank()
    assert list(ranked["rank"]) == list(range(1, len(ranked) + 1))
    assert ranked["id"].is_unique


def test_high_risk_use_cases_go_to_review_first():
    ranked = rank()
    high_risk = ranked[ranked["risk"] >= 5]
    assert (high_risk["recommendation"] == "Review first").all()
    assert ranked.iloc[-len(high_risk):]["risk"].min() >= 5


def test_quick_wins_come_first():
    ranked = rank()
    first_other = ranked.index[ranked["recommendation"] != "Quick win"][0]
    assert (ranked.loc[: first_other - 1, "recommendation"] == "Quick win").all()


def test_ratings_must_be_one_to_five(tmp_path):
    df = load()
    df.loc[0, "value"] = 7
    path = tmp_path / "bad.csv"
    df.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load(path)
    assert isinstance(df, pd.DataFrame)
