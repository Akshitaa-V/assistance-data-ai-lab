# AI Assistant Evaluation: Case Intake

Test set: 25 member messages (English and German) in
`evaluation/test_cases.jsonl`, with the expected category, urgency and the facts every summary
must contain. The rules are in `evaluation/guidelines.md`.

Release gate: category accuracy >= 90%, every urgent case found, fact coverage >= 90%,
all summaries in English and no invented facts.

| System | Category accuracy | Urgency accuracy | Urgent cases found | Fact coverage | English summaries | Invented facts | Passes gate |
|---|---|---|---|---|---|---|---|
| baseline | 96% | 88% | 100% | 100% | 84% | 0 | no (english_summaries) |

### baseline: cases with at least one error

| case_id | expected_category | category | expected_urgency | urgency | fact_coverage | english | unsupported_facts |
|---|---|---|---|---|---|---|---|
| T05 | Breakdown | Breakdown | Normal | High | 100% | True |  |
| T06 | Battery | Battery | Normal | Normal | 100% | False |  |
| T07 | Tyre | Tyre | High | High | 100% | False |  |
| T09 | Travel Assistance | Medical Assistance Abroad | Normal | High | 100% | True |  |
| T15 | Battery | Battery | Normal | High | 100% | False |  |
| T23 | Medical Assistance Abroad | Medical Assistance Abroad | High | High | 100% | False |  |

## How to add another assistant

1. `python -m adl prompt` writes `prompts/copilot_batch_prompt.txt` and an empty `responses/template.csv`.
2. Paste the prompt into the assistant (for example Microsoft Copilot) and save its CSV answer as
   `responses/<name>.csv`.
3. Run `python -m adl evaluate`; every CSV in `responses/` is scored and this page is rewritten.
