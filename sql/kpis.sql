-- KPI library in SQL (SQLite dialect, runs on the star schema in output/powerbi).
-- One query per KPI. The key after "-- name:" matches the KPI key in src/adl/kpis.py,
-- and tests/test_kpis.py checks that every query returns the same value as pandas.

-- name: case_volume
SELECT COUNT(*) AS case_volume
FROM fact_case;

-- name: sla_compliance_rate
SELECT AVG(f.sla_met * 1.0) AS sla_compliance_rate
FROM fact_case AS f
JOIN dim_service AS s ON s.service_key = f.service_key
WHERE s.service_group = 'Road';

-- name: median_arrival_min
WITH road AS (
    SELECT f.arrival_min
    FROM fact_case AS f
    JOIN dim_service AS s ON s.service_key = f.service_key
    WHERE s.service_group = 'Road'
),
ordered AS (
    SELECT arrival_min,
           ROW_NUMBER() OVER (ORDER BY arrival_min) AS rn,
           COUNT(*) OVER () AS n
    FROM road
)
SELECT AVG(arrival_min) AS median_arrival_min
FROM ordered
WHERE rn IN ((n + 1) / 2, (n + 2) / 2);

-- name: on_site_resolution_rate
SELECT AVG(f.resolved_on_site * 1.0) AS on_site_resolution_rate
FROM fact_case AS f
JOIN dim_service AS s ON s.service_key = f.service_key
WHERE s.service_group = 'Road';

-- name: avg_first_contact_min
SELECT AVG(first_contact_min) AS avg_first_contact_min
FROM fact_case;

-- name: csat_avg
SELECT AVG(csat) AS csat_avg
FROM fact_case
WHERE csat IS NOT NULL;

-- name: survey_response_rate
SELECT AVG(CASE WHEN csat IS NOT NULL THEN 1.0 ELSE 0.0 END) AS survey_response_rate
FROM fact_case;

-- name: app_share
SELECT AVG(CASE WHEN c.channel = 'App' THEN 1.0 ELSE 0.0 END) AS app_share
FROM fact_case AS f
JOIN dim_channel AS c ON c.channel_key = f.channel_key;
