# Assistance Data & AI Lab

[![CI](https://github.com/Akshitaa-V/assistance-data-ai-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/Akshitaa-V/assistance-data-ai-lab/actions/workflows/ci.yml)

Data preparation, KPI reporting and the testing of AI assistants for a fictional mobility
assistance service (roadside help, towing, travel and medical assistance abroad).

The project covers the full path from raw data to a decision:

1. **Data preparation**: 24,300 synthetic case records with known data quality problems, cleaned by
   7 validation rules. Faulty rows go to a quarantine file with the reason, so nothing disappears silently.
2. **KPI library**: 8 KPIs (SLA compliance, median arrival time, on-site resolution, CSAT, app share …),
   each defined once with owner, formula, SQL and DAX. Tests check that SQL and pandas give the same numbers.
3. **Reporting**: an Excel workbook with live formulas (`COUNTIFS`, `AVERAGEIFS`, `MEDIAN`), a monthly
   chart and a data quality sheet, plus a star schema and DAX measures for a Power BI report.
4. **Data & AI use cases**: a backlog of 10 ideas (Microsoft 365 Copilot, Copilot in Power BI, Power
   Automate …) rated on value, effort, data readiness and risk, with a success measure for each.
5. **Testing AI assistants before use**: a test set of 25 member messages in English and German, written
   rules for the correct answer, a release gate and a scorer. Any assistant, for example Microsoft Copilot,
   is scored the same way as a rule-based baseline.

All data is synthetic. No real member or company data is used.

## Quick start

```powershell
git clone https://github.com/Akshitaa-V/assistance-data-ai-lab.git
cd assistance-data-ai-lab
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

python -m adl run               # pipeline, Excel report, Power BI tables, docs (about 5 s)
pytest -q                       # 26 tests
```

## Results

Full details in [`docs/RESULTS.md`](docs/RESULTS.md).

| KPI | Value |
|---|---|
| Cases after data quality checks | 23,590 of 24,300 (710 quarantined) |
| SLA compliance (help within 60 min) | 60.6% |
| Median arrival time | 54 min |
| On-site resolution | 65.3% |
| Member satisfaction | 4.41 / 5 |
| App channel share | 26.2% |

Main findings:

- **Winter is the weak season:** 48.1% of road cases met the 60-minute target from December to February,
  against 66.0% in the rest of the year.
- **Regions differ a lot:** SLA compliance ranges from 50.8% (Bavaria) to 76.1% (Berlin).
- **Waiting costs satisfaction:** 4.58/5 when help arrived on time, 4.07/5 when it did not.
- **The digital intake works:** app share rose from 17.6% to 34.0% after the July launch, and app cases
  were confirmed by a dispatcher in 2.4 instead of 5.0 minutes.

## Testing AI assistants

Before an assistant is used with real cases, it has to pass a release gate on the test set in
[`evaluation/`](evaluation): category accuracy of at least 90%, every urgent case found, at least 90% of
the required facts in the summaries, all summaries in English, and no invented facts (places, road numbers
or numbers that are not in the message).

The rule-based baseline sorts 96% of the messages into the right category and finds every urgent case, but
it fails the gate: it cannot turn the German messages into English handovers, and it marks a member who has
already reached a safe exit as urgent. That gap is what an assistant has to close. Results for every system
scored so far are in [`docs/EVALUATION.md`](docs/EVALUATION.md).

To score an assistant:

```powershell
python -m adl prompt      # writes prompts/copilot_batch_prompt.txt and responses/template.csv
# paste the prompt into the assistant, save its CSV answer as responses/copilot.csv
python -m adl evaluate    # scores every CSV in responses/ and rewrites docs/EVALUATION.md
```

## Use-case backlog

[`docs/USE_CASES.md`](docs/USE_CASES.md) ranks 10 Data & AI ideas. Score = 2 × value + data readiness −
effort − risk. Quick wins come first (for example a weekly KPI commentary drafted with Copilot in Power BI,
or dispatcher handover summaries). Use cases with high risk, such as medical triage with health data, are
marked "Review first" whatever their score.

## Power BI

[`powerbi/BUILD.md`](powerbi/BUILD.md) describes the model (one fact table, four dimensions), the report
pages and how to check the numbers against `docs/RESULTS.md`. The DAX measures are in
[`powerbi/DAX_MEASURES.md`](powerbi/DAX_MEASURES.md).

## Project structure

```
src/adl/
  generate.py       synthetic case data with logged data quality problems
  quality.py        7 validation rules, quarantine with reasons
  model.py          star schema for Power BI
  kpis.py           KPI library (pandas + SQL), checked against each other
  excel_report.py   Excel workbook with live formulas and a chart
  usecases.py       use-case scoring and ranking
  evaluate.py       test set, release gate and scorer for AI assistants
  baseline.py       rule-based reference system
  report.py         Markdown reports in docs/
sql/kpis.sql        KPI queries
powerbi/            DAX measures and build guide
evaluation/         guidelines, test cases, place list
data/use_cases.csv  use-case ratings
tests/              26 tests (data quality, KPIs, Excel, evaluation, use cases)
```

## License

MIT
