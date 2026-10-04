# Building the Power BI Report

Power BI Desktop is free for Windows. The steps below take about 45 minutes.

## 1. Load the data

1. Run the pipeline once: `python -m adl run` (creates `output/powerbi/*.csv`).
2. In Power BI Desktop: **Home → Get data → Text/CSV** and load the five files
   `fact_case`, `dim_date`, `dim_region`, `dim_service`, `dim_channel`.
3. In Power Query, check the data types:
   - `fact_case[created_at]` → Date/Time, `dim_date[date]` → Date
   - `arrival_min`, `first_contact_min`, `csat` → Decimal number
   - `sla_met`, `resolved_on_site` → Whole number
4. **Close & Apply**.

## 2. Model

1. Open the **Model view** and create the four relationships listed in
   `DAX_MEASURES.md` (dimension key → fact key, one-to-many, single direction).
2. Mark `dim_date` as the date table.
3. Hide the key columns in `fact_case` so report users only see the dimensions.

## 3. Measures

Create an empty table `_Measures` (**Home → Enter data**) and add every measure
from `DAX_MEASURES.md`. Format the percentages as %, one decimal place.

Check the numbers against `docs/RESULTS.md`. They must match exactly; if one
doesn't, a data type or a relationship is wrong.

## 4. Report pages

**Page 1 – Overview**
- KPI cards: Case Volume, SLA Compliance, Median Arrival (min), On-site Resolution, CSAT
- Line chart: SLA Compliance by `dim_date[month_name]`
- Bar chart: Case Volume by `dim_service[service_type]`
- Slicers: `dim_region[region]`, `dim_date[season]`

**Page 2 – Regions and Operations**
- Bar chart: SLA Compliance by region, sorted ascending (where to look first)
- Matrix: region × season with Median Arrival (min)

**Page 3 – Digital Channels**
- Line chart: App Share by month, with a constant line at July (digital intake launch)
- Cards: App Share Before Launch, App Share After Launch
- Bar chart: Avg First Contact (min) by channel

## 5. Try Copilot in Power BI (optional)

If your account has Copilot in Power BI, open the Copilot pane and use the
"Report page summary" prompts from `prompts/copilot_prompts.md`. Paste the
answers into `responses/copilot.csv` and run `python -m adl evaluate` to score
them against the same test cases as the baseline.

## 6. Save

Save as `powerbi/assistance_kpis.pbix` and add screenshots of the three pages to
`docs/img/` for the README.
