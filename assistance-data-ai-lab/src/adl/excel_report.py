"""Excel KPI report with live formulas.

The workbook is meant for colleagues who work in Excel rather than Power BI.
Every KPI on the summary and monthly sheets is a normal Excel formula over the
Cases sheet (COUNTIFS, AVERAGEIFS, MEDIAN), so the numbers update when rows are
added or filtered copies are made. A check column compares each formula with
the value the Python pipeline computed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from .kpis import KPIS, compute_kpis, kpis_by, _joined
from .model import StarSchema
from .quality import QualityResult

CASE_COLUMNS = [
    "case_id", "created_date", "month", "region", "service_type", "service_group", "channel",
    "vehicle_type", "first_contact_min", "arrival_min", "sla_met", "resolved_on_site", "csat",
]
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")

PCT = "0.0%"
MIN = '0.0" min"'
SCORE = "0.00"
COUNT = "#,##0"
NUMBER_FORMAT = {"count": COUNT, "pct": PCT, "min": MIN, "score": SCORE}


def _cases_frame(star: StarSchema) -> pd.DataFrame:
    df = _joined(star)
    df["created_date"] = pd.to_datetime(df["created_at"]).dt.date
    out = df[CASE_COLUMNS].copy()
    for col in ("sla_met", "resolved_on_site"):
        out[col] = out[col].astype(object).where(out[col].notna(), None)
    for col in ("arrival_min", "csat"):
        out[col] = out[col].astype(object).where(out[col].notna(), None)
    return out


def _style_header(ws, n_cols: int, row: int = 1) -> None:
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")


def kpi_formulas(n_rows: int) -> dict[str, str]:
    """Excel formulas for each KPI over the Cases sheet (rows 2..n_rows+1)."""
    last = n_rows + 1

    def col(name: str) -> str:
        letter = get_column_letter(CASE_COLUMNS.index(name) + 1)
        return f"Cases!${letter}$2:${letter}${last}"

    return {
        "case_volume": f"=COUNTA({col('case_id')})",
        "sla_compliance_rate": f'=AVERAGEIFS({col("sla_met")},{col("service_group")},"Road")',
        "median_arrival_min": f"=MEDIAN({col('arrival_min')})",
        "on_site_resolution_rate": f'=AVERAGEIFS({col("resolved_on_site")},{col("service_group")},"Road")',
        "avg_first_contact_min": f"=AVERAGE({col('first_contact_min')})",
        "csat_avg": f"=AVERAGE({col('csat')})",
        "survey_response_rate": f"=COUNT({col('csat')})/COUNTA({col('case_id')})",
        "app_share": f'=COUNTIFS({col("channel")},"App")/COUNTA({col("case_id")})',
    }


def monthly_formulas(n_rows: int, row: int) -> dict[str, str]:
    """Formulas for one row of the Monthly sheet; the month number sits in column A."""
    last = n_rows + 1

    def col(name: str) -> str:
        letter = get_column_letter(CASE_COLUMNS.index(name) + 1)
        return f"Cases!${letter}$2:${letter}${last}"

    m = f"$A{row}"
    return {
        "case_volume": f"=COUNTIFS({col('month')},{m})",
        "sla_compliance_rate": f'=AVERAGEIFS({col("sla_met")},{col("month")},{m},{col("service_group")},"Road")',
        "on_site_resolution_rate": f'=AVERAGEIFS({col("resolved_on_site")},{col("month")},{m},{col("service_group")},"Road")',
        "csat_avg": f"=AVERAGEIFS({col('csat')},{col('month')},{m})",
        "app_share": f'=COUNTIFS({col("channel")},"App",{col("month")},{m})/COUNTIFS({col("month")},{m})',
    }


MONTHLY_KPIS = ["case_volume", "sla_compliance_rate", "on_site_resolution_rate", "csat_avg", "app_share"]


def build_workbook(star: StarSchema, quality: QualityResult, path: Path) -> Path:
    cases = _cases_frame(star)
    n = len(cases)
    python_kpis = compute_kpis(star)
    monthly = kpis_by(star, "month")

    wb = Workbook()

    # --- KPI Summary -------------------------------------------------------
    ws = wb.active
    ws.title = "KPI Summary"
    ws["A1"] = "Assistance Service KPI Report"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Reporting period {cases['created_date'].min()} to {cases['created_date'].max()}, {n:,} cases after data quality checks."
    headers = ["KPI", "Value (Excel formula)", "Pipeline value", "Check", "Owner", "Business question"]
    ws.append([])
    ws.append(headers)
    _style_header(ws, len(headers), row=4)
    formulas = kpi_formulas(n)
    for i, kpi in enumerate(KPIS, start=5):
        ws.cell(row=i, column=1, value=kpi.name)
        ws.cell(row=i, column=2, value=formulas[kpi.key]).number_format = NUMBER_FORMAT[kpi.unit]
        ws.cell(row=i, column=3, value=python_kpis[kpi.key]).number_format = NUMBER_FORMAT[kpi.unit]
        ws.cell(row=i, column=4, value=f'=IF(ABS(B{i}-C{i})<0.000001,"OK","CHECK")')
        ws.cell(row=i, column=5, value=kpi.owner)
        ws.cell(row=i, column=6, value=kpi.question)
    for letter, width in zip("ABCDEF", (30, 22, 16, 9, 26, 52)):
        ws.column_dimensions[letter].width = width

    # --- Monthly -----------------------------------------------------------
    wm = wb.create_sheet("Monthly")
    m_headers = ["Month", "Month name", "Cases", "SLA compliance", "On-site resolution", "CSAT", "App share"]
    wm.append(m_headers)
    _style_header(wm, len(m_headers))
    fmts = [COUNT, PCT, PCT, SCORE, PCT]
    for r, month in enumerate(monthly["month"].tolist(), start=2):
        wm.cell(row=r, column=1, value=int(month))
        wm.cell(row=r, column=2, value=pd.Timestamp(2025, int(month), 1).strftime("%b"))
        f = monthly_formulas(n, r)
        for c, (key, fmt) in enumerate(zip(MONTHLY_KPIS, fmts), start=3):
            wm.cell(row=r, column=c, value=f[key]).number_format = fmt
    for letter in "ABCDEFG":
        wm.column_dimensions[letter].width = 18

    chart = LineChart()
    chart.title = "SLA compliance and app share by month"
    chart.y_axis.title = "Share of cases"
    chart.y_axis.number_format = "0%"
    chart.x_axis.title = "Month"
    last_row = len(monthly) + 1
    chart.add_data(Reference(wm, min_col=4, min_row=1, max_row=last_row), titles_from_data=True)
    chart.add_data(Reference(wm, min_col=7, min_row=1, max_row=last_row), titles_from_data=True)
    chart.set_categories(Reference(wm, min_col=2, min_row=2, max_row=last_row))
    chart.height, chart.width = 8, 18
    wm.add_chart(chart, "I2")

    # --- Data Quality ------------------------------------------------------
    wq = wb.create_sheet("Data Quality")
    wq.append(["Rule", "Description", "Rows flagged"])
    _style_header(wq, 3)
    for row in quality.summary.itertuples(index=False):
        wq.append([row.rule, row.description, row.rows_flagged])
    wq.append([])
    wq.append(["Rows kept", "", len(quality.clean)])
    wq.append(["Rows quarantined", "", len(quality.quarantine)])
    for letter, width in zip("ABC", (24, 70, 14)):
        wq.column_dimensions[letter].width = width

    # --- KPI Definitions ---------------------------------------------------
    wd = wb.create_sheet("KPI Definitions")
    wd.append(["Key", "KPI", "Owner", "Formula", "Unit"])
    _style_header(wd, 5)
    for kpi in KPIS:
        wd.append([kpi.key, kpi.name, kpi.owner, kpi.formula, kpi.unit])
    for letter, width in zip("ABCDE", (26, 30, 26, 60, 8)):
        wd.column_dimensions[letter].width = width

    # --- Cases (data) ------------------------------------------------------
    wc = wb.create_sheet("Cases")
    wc.append(CASE_COLUMNS)
    for row in cases.itertuples(index=False):
        wc.append(list(row))
    ref = f"A1:{get_column_letter(len(CASE_COLUMNS))}{n + 1}"
    table = Table(displayName="tblCases", ref=ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    wc.add_table(table)
    wc.freeze_panes = "A2"
    for i in range(1, len(CASE_COLUMNS) + 1):
        wc.column_dimensions[get_column_letter(i)].width = 16

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
