# Monitoring Setup and Alert Configuration
**Author:** Diluksha Perera
**Date:** 2026-04-08
**DAG:** retail_daily_ingestion
**Submission:** diluksha-perera-month1-monitoring-setup.md

---

## 1. Airflow UI Monitoring

### Graph View
- **Access:** http://localhost:8080 -> DAGs -> retail_daily_ingestion -> Graph tab
- **Purpose:** Real-time task status during and after DAG run
- **Colour legend:**
  - Dark green = success
  - Red = failed
  - Yellow = running or retrying
  - Pink/light = skipped (branch path not taken)
  - Orange = upstream_failed (cascaded from upstream failure)
- **Usage:** Click any task box -> popup appears -> click Logs
  for full execution output including row counts and errors

### Gantt Chart
- **Access:** Graph tab -> click Gantt tab
- **Purpose:** Task duration analysis and bottleneck detection
- **Usage:** Compare horizontal bar widths across runs to detect
  performance degradation over time
- **Verified run (2026-04-08):** Full pipeline completes in ~20s
  for 10,050-row dataset. Production with 500K rows expected ~90s.

### Task Logs
- **Access:** Click task box in Graph -> Logs tab
- **Key log lines in ingest_to_staging:**
  ```
  Reading s3://raw-data/retail-data/2026-04-07/sales_transactions.csv
  File sales_transactions.csv loaded: 10050 rows
  Staged 10050 rows -> staging.sales_transactions
  File product_catalog.csv loaded: 200 rows
  Staged 200 rows -> staging.product_catalog
  File store_locations.csv loaded: 50 rows
  Staged 50 rows -> staging.store_locations
  staging.sales_transactions row count: 10050
  ```
- **Key log lines in transform_sales:**
  ```
  Transform input: 10050 rows from staging
  Wrote 50 invalid rows to staging.error_log
  Filter removed 50 invalid rows
  Aggregated to 6361 store-product-date rows
  Enriched dataset: 6361 rows ready for curated load
  Wrote 6361 rows to staging.fact_daily_sales_stage
  ```

### Run Duration View
- **Access:** DAG page -> Run Duration tab
- **Purpose:** Track pipeline duration trends across runs
- **Usage:** Detect if pipeline is slowing down over time

---

## 2. Alert Configuration

### Slack Webhook Alerts (implemented and verified)

**Connection:** Admin -> Connections -> slack_webhook
| Field | Value |
|---|---|
| Connection Id | slack_webhook |
| Type | HTTP |
| Host | https://hooks.slack.com/services |
| Password | Webhook path (stored encrypted) |

**Channel:** #pipeline-alerts (Bistecglobal workspace)

**Alert types:**

Task failure alert (fires on any task failure):
```
RED CIRCLE Pipeline Failure Alert
DAG:   retail_daily_ingestion
Task:  ingest_to_staging
Date:  2026-04-07
Status: Failed
Exception: [first 500 chars of traceback]
Check Airflow logs for full traceback.
```

Pipeline completion notification (fires on send_notification task):
```
CHECK MARK Pipeline SUCCESS
DAG:          retail_daily_ingestion
Run Date:     2026-04-07
Status:       SUCCESS
Failed Tasks: None
```

**Verified working:** Slack message received on 2026-04-08 run
showing Pipeline SUCCESS with correct run date and status.

### Row Count Anomaly Alert
```python
# In ingest_to_staging task
if count < 100:
    raise AirflowException(
        f"Anomaly detected: only {count} rows. Expected >=100."
    )
```
Triggers task failure -> Slack failure alert -> pipeline abort.

### SLA Miss Configuration
```python
default_args = {
    ...
    "sla": timedelta(hours=2),
}
```
All tasks must complete within 2 hours. Airflow raises SLA miss
event if exceeded. Production: configure SMTP for SLA miss email.

### DAG-Level Callbacks
```python
on_failure_callback=send_failure_alert,  # fires on DAG failure
on_success_callback=dag_success_callback, # logs on DAG success
```

---

## 3. Verified Production Run Evidence

### Run: 2026-04-08 (data_interval_start: 2026-04-07)

**Task execution sequence (all green):**
```
check_files_exist  -> SUCCESS (sensor found all 3 files)
branch_on_files    -> SUCCESS (routed to ingest_to_staging)
alert_missing_files-> SKIPPED (happy path taken)
ingest_to_staging  -> SUCCESS (10,050 rows loaded)
transform_sales    -> SUCCESS (6,361 rows aggregated)
load_curated       -> SUCCESS (UPSERT complete)
archive_source_files-> SUCCESS (files copied to archive-data)
send_notification  -> SUCCESS (Slack message delivered)
```

**Database row counts after run:**
| Table | Row Count |
|---|---|
| staging.sales_transactions | 10,050 |
| staging.product_catalog | 200 |
| staging.store_locations | 50 |
| staging.error_log | 50 (bad rows captured) |
| staging.fact_daily_sales_stage | 6,361 |
| curated.fact_daily_sales | 6,361 |

**Revenue by category (curated layer):**
| Category | Stores | Products | Units Sold | Revenue |
|---|---|---|---|---|
| Home | 50 | 44 | 21,647 | 9,929,466.51 |
| Electronics | 50 | 44 | 21,394 | 9,820,171.78 |
| Health | 50 | 40 | 21,514 | 9,735,957.78 |
| Clothing | 50 | 44 | 20,246 | 9,307,953.20 |
| Food | 50 | 44 | 20,048 | 9,048,003.30 |

---

## 4. Production Monitoring Recommendations

| Enhancement | Tool | Priority |
|---|---|---|
| SMTP email alerts | Airflow SMTP Connection | High |
| Row count trend dashboard | Power BI on curated schema | High |
| Data quality checks | Great Expectations integration | Medium |
| SLA miss email | Configure SMTP + sla parameter | Medium |
| Pipeline metrics | Custom logging to metrics table | Low |
