import pytest

from adl.kpis import DAX_FILE, KPIS, compute_kpis, compute_kpis_sql, kpis_by, load_sql_queries


def test_sql_and_pandas_agree(star):
    pandas_kpis = compute_kpis(star)
    sql_kpis = compute_kpis_sql(star)
    assert set(pandas_kpis) == set(sql_kpis)
    for key, value in pandas_kpis.items():
        assert sql_kpis[key] == pytest.approx(value, abs=1e-9), key


def test_every_kpi_has_sql_and_dax():
    sql = load_sql_queries()
    dax = DAX_FILE.read_text(encoding="utf-8")
    for kpi in KPIS:
        assert kpi.key in sql, f"{kpi.key} missing in sql/kpis.sql"
        assert f"### {kpi.key}" in dax, f"{kpi.key} missing in DAX_MEASURES.md"


def test_rates_are_between_zero_and_one(star):
    k = compute_kpis(star)
    for key in ("sla_compliance_rate", "on_site_resolution_rate", "survey_response_rate", "app_share"):
        assert 0 <= k[key] <= 1


def test_monthly_volumes_add_up(star):
    monthly = kpis_by(star, "month")
    assert len(monthly) == 12
    assert monthly["case_volume"].sum() == compute_kpis(star)["case_volume"]


def test_star_schema_keys_are_complete(star):
    fact = star.fact_case
    assert fact["region_key"].isin(star.dim_region["region_key"]).all()
    assert fact["service_key"].isin(star.dim_service["service_key"]).all()
    assert fact["channel_key"].isin(star.dim_channel["channel_key"]).all()
    assert fact["date_key"].isin(star.dim_date["date_key"]).all()


def test_sla_flag_only_for_road_services(star):
    fact = star.fact_case.merge(star.dim_service, on="service_key")
    assert fact.loc[fact["service_group"] == "Remote", "sla_met"].isna().all()
    assert fact.loc[fact["service_group"] == "Road", "sla_met"].notna().all()
