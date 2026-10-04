# DAX Measures

These measures implement the KPI library in `src/adl/kpis.py` on the star schema in
`output/powerbi/`. Each heading is the KPI key, so the tests can check that every KPI
has a measure. Create them in a separate `_Measures` table in Power BI Desktop.

Relationships (all single direction, one-to-many from the dimension):

- `dim_date[date_key]` → `fact_case[date_key]`
- `dim_region[region_key]` → `fact_case[region_key]`
- `dim_service[service_key]` → `fact_case[service_key]`
- `dim_channel[channel_key]` → `fact_case[channel_key]`

### case_volume

```dax
Case Volume = COUNTROWS ( fact_case )
```

### sla_compliance_rate

```dax
SLA Compliance =
CALCULATE (
    AVERAGE ( fact_case[sla_met] ),
    dim_service[service_group] = "Road"
)
```

### median_arrival_min

```dax
Median Arrival (min) =
CALCULATE (
    MEDIAN ( fact_case[arrival_min] ),
    dim_service[service_group] = "Road"
)
```

### on_site_resolution_rate

```dax
On-site Resolution =
CALCULATE (
    AVERAGE ( fact_case[resolved_on_site] ),
    dim_service[service_group] = "Road"
)
```

### avg_first_contact_min

```dax
Avg First Contact (min) = AVERAGE ( fact_case[first_contact_min] )
```

### csat_avg

```dax
CSAT = AVERAGE ( fact_case[csat] )
```

### survey_response_rate

```dax
Survey Response Rate =
DIVIDE ( COUNT ( fact_case[csat] ), [Case Volume] )
```

### app_share

```dax
App Share =
DIVIDE (
    CALCULATE ( [Case Volume], dim_channel[channel] = "App" ),
    [Case Volume]
)
```

## Helper measures for the report pages

```dax
SLA Compliance vs Prior Month =
VAR CurrentMonth = [SLA Compliance]
VAR PriorMonth =
    CALCULATE ( [SLA Compliance], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN
    CurrentMonth - PriorMonth
```

```dax
App Share Before Launch =
CALCULATE ( [App Share], dim_date[date] < DATE ( 2025, 7, 1 ) )
```

```dax
App Share After Launch =
CALCULATE ( [App Share], dim_date[date] >= DATE ( 2025, 7, 1 ) )
```

For the time intelligence measures, mark `dim_date` as the date table
(Table tools → Mark as date table → `date`).
