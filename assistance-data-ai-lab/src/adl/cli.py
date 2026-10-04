"""Command line entry point.

    python -m adl run        # data pipeline, Excel report, Power BI files, all docs
    python -m adl prompt     # write the assistant prompt and an empty answer template
    python -m adl evaluate   # score every CSV in responses/ and rewrite docs/EVALUATION.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import baseline
from .evaluate import build_batch_prompt, load_responses, score, write_response_template
from .excel_report import build_workbook
from .generate import generate
from .kpis import compute_kpis, compute_kpis_sql, format_value, KPIS
from .model import build_star_schema
from .quality import run_checks
from .report import evaluation_markdown, results_markdown, use_cases_markdown
from .usecases import rank

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
DOCS = ROOT / "docs"
RESPONSES = ROOT / "responses"
PROMPTS = ROOT / "prompts"


def cmd_prompt() -> None:
    PROMPTS.mkdir(exist_ok=True)
    path = PROMPTS / "copilot_batch_prompt.txt"
    path.write_text(build_batch_prompt(), encoding="utf-8")
    write_response_template(RESPONSES / "template.csv")
    print(f"Prompt:   {path.relative_to(ROOT)}")
    print(f"Template: {(RESPONSES / 'template.csv').relative_to(ROOT)}")


def cmd_evaluate() -> None:
    baseline.write_csv(RESPONSES / "baseline.csv", baseline.run())
    results = {}
    for path in sorted(RESPONSES.glob("*.csv")):
        if path.name == "template.csv":
            continue
        responses = load_responses(path)
        if responses[["category", "urgency", "summary"]].eq("").all(axis=None):
            print(f"Skipping {path.name}: no answers yet")
            continue
        results[path.stem] = score(responses)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "EVALUATION.md").write_text(evaluation_markdown(results), encoding="utf-8")
    for name, (m, _) in results.items():
        status = "passes" if m["passes_gate"] else "fails"
        print(f"{name:>12}: category {m['category_accuracy']:.0%}, urgent found {m['high_urgency_recall']:.0%}, "
              f"facts {m['fact_coverage']:.0%}, English {m['english_summaries']:.0%} -> {status} the gate")


def cmd_run() -> None:
    data = generate()
    quality = run_checks(data.cases)
    star = build_star_schema(quality.clean)

    OUTPUT.mkdir(exist_ok=True)
    data.cases.to_csv(OUTPUT / "cases_raw.csv", index=False)
    quality.quarantine.to_csv(OUTPUT / "quarantine.csv", index=False)
    star.to_csv(OUTPUT / "powerbi")
    build_workbook(star, quality, OUTPUT / "assistance_kpi_report.xlsx")

    pandas_kpis = compute_kpis(star)
    sql_kpis = compute_kpis_sql(star)
    for key, value in pandas_kpis.items():
        if abs(value - sql_kpis[key]) > 1e-9:
            raise SystemExit(f"KPI {key}: pandas {value} != SQL {sql_kpis[key]}")

    DOCS.mkdir(exist_ok=True)
    (DOCS / "RESULTS.md").write_text(results_markdown(star, quality), encoding="utf-8")
    (DOCS / "USE_CASES.md").write_text(use_cases_markdown(rank()), encoding="utf-8")
    cmd_prompt()
    cmd_evaluate()

    print(f"\n{len(data.cases):,} rows loaded, {len(quality.quarantine):,} quarantined, {len(quality.clean):,} kept")
    for kpi in KPIS:
        print(f"  {kpi.name:<28} {format_value(kpi.key, pandas_kpis[kpi.key])}")
    print("\nOutputs: output/ (CSV, Excel, Power BI tables) and docs/ (results, use cases, evaluation)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="adl", description="Assistance Data & AI Lab")
    parser.add_argument("command", choices=["run", "prompt", "evaluate"])
    args = parser.parse_args(argv)
    {"run": cmd_run, "prompt": cmd_prompt, "evaluate": cmd_evaluate}[args.command]()


if __name__ == "__main__":
    main()
