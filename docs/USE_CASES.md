# Data & AI Use-Case Backlog

Each idea is rated 1-5 on value, effort, data readiness and risk.
Score = 2 x value + data readiness - effort - risk. Ideas with risk 5 (for example health data)
are marked "Review first" whatever their score: they need a data protection review before any test.

| rank | id | title | tool | value | effort | data ready | risk | score | recommendation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | UC03 | Weekly KPI commentary draft | Copilot in Power BI | 4 | 1 | 5 | 1 | 11 | Quick win |
| 2 | UC01 | Dispatcher handover summary | Microsoft 365 Copilot | 5 | 2 | 4 | 3 | 9 | Quick win |
| 3 | UC05 | Reply drafts for travel assistance emails | Copilot in Outlook | 4 | 2 | 4 | 3 | 7 | Quick win |
| 4 | UC07 | SLA early warning per region | Power BI alerts + Power Automate | 5 | 3 | 5 | 1 | 11 | Strategic project |
| 5 | UC02 | Categorise app and web case submissions | Copilot Studio / Python | 5 | 3 | 4 | 3 | 8 | Strategic project |
| 6 | UC09 | Knowledge base answers for service agents | Copilot with SharePoint | 4 | 3 | 3 | 2 | 6 | Strategic project |
| 7 | UC04 | Meeting notes to action items | Copilot in Teams | 3 | 1 | 5 | 2 | 8 | Small improvement |
| 8 | UC06 | Data preparation in Excel with Copilot | Copilot in Excel | 3 | 1 | 4 | 1 | 8 | Small improvement |
| 9 | UC10 | Themes from survey comments | Python / Copilot in Excel | 3 | 2 | 3 | 2 | 5 | Small improvement |
| 10 | UC08 | Medical case triage support abroad | Microsoft 365 Copilot | 5 | 4 | 2 | 5 | 3 | Review first |

## How success is measured

Every use case gets a measurable success criterion before work starts:

- **UC03 Weekly KPI commentary draft** (Reporting, Team leads): Draft needs fewer than 3 corrections; numbers match the report
- **UC01 Dispatcher handover summary** (Case intake, Dispatchers): Fact coverage >= 90% and no invented facts on the intake test set
- **UC05 Reply drafts for travel assistance emails** (Member communication, Travel assistance agents): Agent edits fewer than 20% of the draft; tone checked by a team lead
- **UC07 SLA early warning per region** (Operations steering, Operations managers): Alert fires within one day when weekly SLA drops by 5 points
- **UC02 Categorise app and web case submissions** (Case intake, Dispatchers): Category accuracy >= 90% and no missed urgent case
- **UC09 Knowledge base answers for service agents** (Agent support, Contact centre agents): Correct source cited in >= 95% of test questions
- **UC04 Meeting notes to action items** (Internal meetings, All teams): Action items complete when checked against the recording
- **UC06 Data preparation in Excel with Copilot** (Reporting, Data analysts): Formulas checked against a manual calculation on 3 sheets
- **UC10 Themes from survey comments** (Member experience, Member experience team): Themes agree with a manual sample of 100 comments
- **UC08 Medical case triage support abroad** (Medical assistance, Medical assistance staff): Only after data protection and medical review

## Next step for the top use case

UC01 (dispatcher handover summary) is tested with the intake test set in `evaluation/`.
See `docs/EVALUATION.md` for the results and the release gate.
