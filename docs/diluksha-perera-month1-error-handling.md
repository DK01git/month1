# Error Handling and Retry Configuration
**Author:** Diluksha Perera
**Date:** 2026-04-08
**DAG:** retail_daily_ingestion
**Submission:** diluksha-perera-month1-error-handling.md

---

## 1. DAG-Level Configuration

```python
default_args = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "email": ["diluksha@bistcglobal.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "sla": timedelta(hours=2),  # Challenge File, Part 4
}

dag = DAG(
    dag_id="retail_daily_ingestion",
    ...
    dagrun_timeout=timedelta(hours=4),
    max_active_runs=1,
    on_failure_callback=send_failure_alert,
    on_success_callback=dag_success_callback,
)
```

**dagrun_timeout:** Entire pipeline aborts after 4 hours — prevents zombie runs.

**max_active_runs=1:** Prevents concurrent runs from truncating
staging.sales_transactions while a previous run's transform_sales
task is still reading from it. Critical for idempotency.

**sla=timedelta(hours=2):** All tasks must complete within 2 hours
or Airflow raises an SLA miss event.

---

## 2. Task-Level Retry Policies

| Task | Retries | Retry Delay | Failure Behaviour |
|---|---|---|---|
| check_files_exist | Sensor poke | 30s poke, 1800s timeout | Pokes MinIO every 30s for up to 30 min |
| ingest_to_staging | 3 | 30s | Retries on MinIO/PostgreSQL transient errors |
| transform_sales | 1 | 30s | Single retry — logic errors need investigation |
| load_curated | 3 | 30s | Retries on transient PostgreSQL connection issues |
| archive_source_files | 2 | 30s | Non-critical — pipeline not blocked on failure |
| send_notification | 0 | N/A | Notify once only, no retry |

---

## 3. Failure Callback — Slack Alert

All tasks use `on_failure_callback=send_failure_alert`.
Implemented via `HttpHook` and Airflow Connection `slack_webhook`.

```python
def send_failure_alert(context):
    dag_id    = context["dag"].dag_id
    task_id   = context["task_instance"].task_id
    run_date  = context.get("ds", "unknown")
    exception = str(context.get("exception", "No exception details"))

    # Posts structured Slack message with:
    # - DAG name
    # - Failed task name
    # - Run date
    # - Exception message (first 500 chars)
    # - Link to check Airflow logs
```

**Slack Connection (Admin -> Connections):**
| Field | Value |
|---|---|
| Connection Id | slack_webhook |
| Type | HTTP |
| Host | https://hooks.slack.com/services |
| Password | /TXXXXXXX/BXXXXXXX/XXXXXXXX (webhook path) |

Webhook path stored in Password field — not hardcoded in DAG code.
Challenge File, Common Mistakes: "Hardcoding connection strings"

**Note on email:** `email_on_failure=True` is configured in
default_args per the challenge file requirement. No SMTP server
is available in the local Docker environment. Slack webhook
satisfies the intent of the requirement — real-time failure
alerting. Production deployment would add an SMTP Airflow
Connection for email delivery.

---

## 4. Dead-Letter Handling

### Pattern 1 — Missing Source Files
```
S3KeySensor confirms sales_transactions.csv exists
       |
BranchPythonOperator checks ALL 3 files via S3Hook.check_for_key()
       |                          |
all 3 present              any file missing
       |                          |
ingest_to_staging          alert_missing_files
                             raises Exception with
                             list of missing paths
                                  |
                           send_notification
                           (trigger_rule=ALL_DONE)
```

### Pattern 2 — Invalid Rows During Transformation
```python
# Identify bad rows BEFORE filtering
bad_mask = ~(
    df["transaction_id"].notna() &
    (df["quantity"].astype(float) > 0) &
    (df["unit_price"].astype(float) > 0)
)

# Write to staging.error_log — not silently dropped
pg_hook.insert_rows(
    table="staging.error_log",
    rows=error_rows,
    target_fields=["source_table", "raw_data", "error_message"],
)
```

**Verified in production test run (2026-04-08):**
- 50 intentional bad rows introduced in test data
- 50 rows captured in staging.error_log per run
- error_message: "Failed filter: null transaction_id or quantity/unit_price <= 0"
- raw_data: full row serialized as JSON for investigation

**staging.error_log schema:**
```sql
CREATE TABLE staging.error_log (
    error_id      SERIAL PRIMARY KEY,
    source_table  VARCHAR(100),
    raw_data      TEXT,          -- full bad row as JSON
    error_message TEXT,          -- reason for rejection
    logged_at     TIMESTAMP DEFAULT NOW()
);
```

### Pattern 3 — Row Count Anomaly Detection
```python
count = pg_hook.get_first(
    "SELECT COUNT(*) FROM staging.sales_transactions;"
)[0]
if count < 100:
    raise AirflowException(
        f"Anomaly detected: only {count} rows. Expected >=100."
    )
```
Challenge File, Part 4: "If count < 100 raise AirflowException"
Pipeline aborts and alerts if ingested row count is suspiciously low.
In production with ~500K rows/day this threshold would be ~100,000.

---

## 5. Idempotency — Safe Reruns

### Staging Layer — TRUNCATE + INSERT:
```sql
TRUNCATE TABLE staging.sales_transactions;
INSERT INTO staging.sales_transactions ...
```
Rerun 10 times — always exactly one copy of source data.

### Curated Layer — UPSERT:
```sql
INSERT INTO curated.fact_daily_sales ...
ON CONFLICT (store_id, product_id, transaction_date)
DO UPDATE SET ...
```
Rerun 10 times — same rows updated in place, never duplicated.
Previous days' data is never affected.

---

## 6. Monitoring via Airflow UI

| What to Monitor | Where | Action |
|---|---|---|
| Task failures | Graph view — red boxes | Click -> Logs for traceback |
| Retry attempts | Graph view — yellow boxes | Click -> Logs for retry count |
| Long running tasks | Gantt tab | Compare bar widths across runs |
| SLA misses | Airflow sends alert | Investigate slow tasks |
| Row count anomaly | ingest_to_staging log | Search "Anomaly" in log |
| Slack alerts | #pipeline-alerts channel | Check failed task and exception |
