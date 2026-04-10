# Month 1 — Project Runbook
**Author:** Diluksha Perera
**Project:** Retail Data Ingestion Pipeline
**Stack:** Apache Airflow + MinIO + PostgreSQL (Docker)
**Purpose:** Step-by-step guide to start, operate, and verify
the pipeline from a cold start (all windows closed, containers stopped)

---

## Prerequisites Checklist

Before running any commands, confirm these are installed:
- Docker Desktop (running — check system tray)
- Python 3.10+ with boto3 and pandas
- DBeaver Community
- VS Code

---

## PART 1 — Cold Start (Everything Stopped)

### Step 1 — Navigate to project folder

```powershell
cd C:\de-training\month1
```

### Step 2 — Stop conflicting container (IMPORTANT)

Your machine has a pre-existing PostgreSQL container from another
project that conflicts with port 5432. Stop it first.

```powershell
docker stop jobapply-postgres
```

If it's already stopped this command returns an error — ignore it
and continue.

### Step 3 — Start all containers

```powershell
docker-compose up -d
```

Wait 60 seconds for all services to initialise.

### Step 4 — Verify all containers are healthy

```powershell
docker-compose ps
```

Expected output — all 5 containers must show healthy or running:

```
NAME                         STATUS
month1-airflow-scheduler-1   Up (running)
month1-airflow-webserver-1   Up (healthy)
month1-minio-1               Up (healthy)
month1-postgres-meta-1       Up (healthy)
month1-postgres-retail-1     Up (healthy)
```

If any container is missing or shows "Exit" — see
Troubleshooting section at the bottom of this runbook.

### Step 5 — Verify postgres-retail network connection

```powershell
docker exec -it month1-airflow-webserver-1 bash -c "nc -zv postgres-retail 5432"
```

Expected: `Connection to postgres-retail (172.20.x.x) 5432 succeeded`

If it fails — run the network fix:

```powershell
docker network disconnect month1_default month1-postgres-retail-1
docker network connect --alias postgres-retail month1_default month1-postgres-retail-1
```

Then verify again.

### Step 6 — Verify database schemas exist

```powershell
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "\dt staging.*"
```

Expected — 5 tables:
```
staging | error_log
staging | fact_daily_sales_stage
staging | product_catalog
staging | sales_transactions
staging | store_locations
```

If tables are missing — recreate them:

```powershell
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;

CREATE TABLE IF NOT EXISTS staging.sales_transactions (
    transaction_id VARCHAR(50), store_id VARCHAR(50),
    product_id VARCHAR(50), quantity INTEGER,
    unit_price NUMERIC(10,2), discount_pct NUMERIC(5,2),
    transaction_date DATE, payment_method VARCHAR(50),
    customer_id VARCHAR(50));

CREATE TABLE IF NOT EXISTS staging.product_catalog (
    product_id VARCHAR(50), product_name VARCHAR(255),
    category VARCHAR(100), subcategory VARCHAR(100),
    brand VARCHAR(100), cost_price NUMERIC(10,2),
    list_price NUMERIC(10,2), supplier_id VARCHAR(50));

CREATE TABLE IF NOT EXISTS staging.store_locations (
    store_id VARCHAR(50), store_name VARCHAR(255),
    city VARCHAR(100), state VARCHAR(100),
    region VARCHAR(100), store_type VARCHAR(50),
    opening_date DATE);

CREATE TABLE IF NOT EXISTS staging.fact_daily_sales_stage (
    store_id VARCHAR(50), product_id VARCHAR(50),
    transaction_date DATE, category VARCHAR(100),
    subcategory VARCHAR(100), brand VARCHAR(100),
    total_quantity INTEGER, total_revenue NUMERIC(12,2),
    total_tax NUMERIC(12,2), transaction_count INTEGER,
    avg_discount NUMERIC(5,2), load_timestamp TIMESTAMP);

CREATE TABLE IF NOT EXISTS staging.error_log (
    error_id SERIAL PRIMARY KEY, source_table VARCHAR(100),
    raw_data TEXT, error_message TEXT,
    logged_at TIMESTAMP DEFAULT NOW());

CREATE TABLE IF NOT EXISTS curated.fact_daily_sales (
    store_id VARCHAR(50), product_id VARCHAR(50),
    transaction_date DATE, category VARCHAR(100),
    subcategory VARCHAR(100), brand VARCHAR(100),
    total_quantity INTEGER, total_revenue NUMERIC(12,2),
    total_tax NUMERIC(12,2), transaction_count INTEGER,
    avg_discount NUMERIC(5,2), load_timestamp TIMESTAMP,
    PRIMARY KEY (store_id, product_id, transaction_date));"
```

---

## PART 2 — Verify Airflow UI

### Step 7 — Open Airflow UI

Open browser: `http://localhost:8080`

```
Username: airflow
Password: airflow
```

If login fails — recreate the admin user:

```powershell
docker exec -it month1-airflow-webserver-1 airflow users create --username airflow --password airflow --firstname Admin --lastname User --role Admin --email admin@example.com
```

### Step 8 — Verify Airflow Connections exist

In Airflow UI: Admin → Connections

Confirm these 3 connections exist:

| Connection ID | Type |
|---|---|
| minio_s3 | Amazon Web Services |
| postgres_retail | Postgres |
| slack_webhook | HTTP |

If any are missing — recreate via Admin → Connections → "+" button:

**minio_s3:**
```
Connection Id:          minio_s3
Connection Type:        Amazon Web Services
AWS Access Key ID:      minioadmin
AWS Secret Access Key:  minioadmin
Extra:                  {"endpoint_url": "http://minio:9000"}
```

**postgres_retail:**
```
Connection Id:    postgres_retail
Connection Type:  Postgres
Host:             postgres-retail
Database:         retailco
Login:            retailco
Password:         retailco
Port:             5432
```

**slack_webhook:**
```
Connection Id:    slack_webhook
Connection Type:  HTTP
Host:             https://hooks.slack.com/services
Password:         /TXXXXXXX/BXXXXXXX/XXXXXXXXXX
```

### Step 9 — Verify Airflow Variable exists

In Airflow UI: Admin → Variables

Confirm this variable exists:

| Key | Value |
|---|---|
| source_bucket | raw-data |

If missing — create via Admin → Variables → "+" button.

### Step 10 — Verify DAG is loaded

```powershell
docker exec -it month1-airflow-webserver-1 bash -c "airflow dags list | grep retail"
```

Expected:
```
retail_daily_ingestion | ... | False
```

If DAG is missing — check the dags folder:

```powershell
ls C:\de-training\month1\dags\
```

Must contain `retail_daily_ingestion.py`. If missing, copy it back.

Check for import errors:

```powershell
docker exec -it month1-airflow-webserver-1 bash -c "airflow dags list-import-errors"
```

Must return empty. If errors shown — paste them and investigate.

---

## PART 3 — Upload Sample Data

### Step 11 — Open MinIO Console

Open browser: `http://localhost:9001`

```
Username: minioadmin
Password: minioadmin
```

### Step 12 — Generate and upload realistic sample data

```powershell
cd C:\de-training\month1
python generate_realistic_data.py
```

Expected output:
```
Generating realistic data for: YYYY-MM-DD
✔ Bucket 'raw-data' already exists.
✔ Uploaded: retail-data/YYYY-MM-DD/store_locations.csv     (50 rows)
✔ Uploaded: retail-data/YYYY-MM-DD/product_catalog.csv    (200 rows)
✔ Uploaded: retail-data/YYYY-MM-DD/sales_transactions.csv (10,050 rows)
```

Note the date printed — you will need it in Step 13.

### Step 13 — Verify files in MinIO

Open `http://localhost:9001` → Object Browser → raw-data →
retail-data → {date from Step 12}

Confirm 3 files exist:
- sales_transactions.csv
- product_catalog.csv
- store_locations.csv

---

## PART 4 — Run the Pipeline

### Step 14 — Trigger the DAG

```powershell
docker exec -it month1-airflow-webserver-1 airflow dags trigger retail_daily_ingestion
```

Note the `data_interval_start` date in the output.

### Step 15 — Verify date matches uploaded data

The `data_interval_start` from Step 14 must match the date
from Step 12. If they don't match — upload data for the correct date:

Open `generate_realistic_data.py` and change:
```python
RUN_DATE = "YYYY-MM-DD"  # use data_interval_start date here
```

Then re-run Step 12.

### Step 16 — Monitor the pipeline

Open `http://localhost:8080` → DAGs → retail_daily_ingestion → Graph tab

Select the latest run in the run selector dropdown.
Enable Auto-refresh toggle (top right).

Watch tasks turn green left to right:
```
check_files_exist    → green (sensor found files)
branch_on_files      → green (all 3 files confirmed)
alert_missing_files  → pink/skipped (happy path taken)
ingest_to_staging    → green (10,050 rows loaded)
transform_sales      → green (6,361 rows aggregated)
load_curated         → green (UPSERT complete)
archive_source_files → green (files archived)
send_notification    → green (Slack message sent)
```

Check Slack #pipeline-alerts for SUCCESS message.

---

## PART 5 — Verify Results

### Step 17 — Verify database counts

```powershell
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "
SELECT 'staging.sales_transactions' , COUNT(*) FROM staging.sales_transactions
UNION ALL
SELECT 'staging.error_log'          , COUNT(*) FROM staging.error_log
UNION ALL
SELECT 'staging.product_catalog'    , COUNT(*) FROM staging.product_catalog
UNION ALL
SELECT 'staging.store_locations'    , COUNT(*) FROM staging.store_locations
UNION ALL
SELECT 'curated.fact_daily_sales'   , COUNT(*) FROM curated.fact_daily_sales;"
```

Expected:
```
staging.sales_transactions  | 10050
staging.error_log            |    50
staging.product_catalog      |   200
staging.store_locations      |    50
curated.fact_daily_sales     |  6361
```

### Step 18 — Verify curated data quality

```powershell
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "
SELECT category,
       COUNT(DISTINCT store_id)   AS stores,
       COUNT(DISTINCT product_id) AS products,
       SUM(total_quantity)        AS units_sold,
       ROUND(SUM(total_revenue)::NUMERIC, 2) AS revenue
FROM curated.fact_daily_sales
GROUP BY category
ORDER BY revenue DESC;"
```

Expected — 5 categories, all 50 stores represented.

### Step 19 — Verify error log captured bad rows

```powershell
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "
SELECT error_id, source_table, error_message, logged_at
FROM staging.error_log
ORDER BY logged_at DESC
LIMIT 5;"
```

Expected — rows with error_message:
`"Failed filter: null transaction_id or quantity/unit_price <= 0"`

### Step 20 — Verify transaction count integrity

```powershell
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "
SELECT SUM(transaction_count) AS total_transactions
FROM curated.fact_daily_sales;"
```

Expected: `10000` — all valid transactions accounted for.

---

## PART 6 — Connect DBeaver

### Step 21 — Connect DBeaver to retailco database

Open DBeaver → New Connection → PostgreSQL:

```
Host:     localhost
Port:     5432
Database: retailco
Username: retailco
Password: retailco
```

Click Test Connection — must show green "Connected".

Note: This only works while jobapply-postgres is stopped (Step 2).
If connection fails, re-run Step 2.

---

## PART 7 — Shutdown

### When done for the day — stop all containers:

```powershell
cd C:\de-training\month1
docker-compose stop
```

### To completely remove containers but keep data volumes:

```powershell
docker-compose down
```

### To remove everything including data (full reset):

```powershell
docker-compose down -v
```

WARNING: `-v` deletes all PostgreSQL data and MinIO files.
Only use if you want to start completely fresh.

---

## TROUBLESHOOTING

### Problem: postgres-retail not showing in docker-compose ps

```powershell
docker-compose up -d postgres-retail
```

### Problem: Airflow webserver not healthy after 2 minutes

```powershell
docker-compose logs airflow-webserver | tail -30
```

Look for error messages. Most common cause — postgres-meta not ready.
Wait 30 more seconds and check again.

### Problem: DAG shows import error in Airflow UI

```powershell
docker exec -it month1-airflow-webserver-1 bash -c "airflow dags list-import-errors"
```

Paste the error. Common causes:
- Missing provider package — check _PIP_ADDITIONAL_REQUIREMENTS in docker-compose.yml
- Syntax error in DAG file — check retail_daily_ingestion.py

### Problem: Sensor times out (check_files_exist fails after 30 min)

Check what date the sensor is looking for:
- Click check_files_exist in Graph → Logs
- Find "Poking for key" line
- Note the date in the path

Upload data for that exact date:
```powershell
# Edit generate_realistic_data.py
# Set RUN_DATE = "the date from sensor log"
python generate_realistic_data.py
```

### Problem: ingest_to_staging fails with "postgres-retail not known"

Network alias lost. Re-attach:
```powershell
docker network disconnect month1_default month1-postgres-retail-1
docker network connect --alias postgres-retail month1_default month1-postgres-retail-1
docker exec -it month1-airflow-webserver-1 bash -c "nc -zv postgres-retail 5432"
```

### Problem: MinIO login fails

Check password in docker-compose.yml:
```yaml
MINIO_ROOT_USER: minioadmin
MINIO_ROOT_PASSWORD: minioadmin  ← must match what you type
```

If password was changed, wipe MinIO volume and restart:
```powershell
docker-compose stop minio
docker volume rm month1_minio-data
docker-compose up -d minio
```

### Problem: DBeaver connection timeout

jobapply-postgres is running and owns port 5432:
```powershell
docker stop jobapply-postgres
```

Then reconnect DBeaver.

---

## QUICK REFERENCE

### Service URLs
| Service | URL | Credentials |
|---|---|---|
| Airflow UI | http://localhost:8080 | airflow / airflow |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| PostgreSQL | localhost:5432 | retailco / retailco / retailco |

### Key Commands
```powershell
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# Trigger pipeline
docker exec -it month1-airflow-webserver-1 airflow dags trigger retail_daily_ingestion

# Check row counts
docker exec -it month1-postgres-retail-1 psql -U retailco -d retailco -c "SELECT COUNT(*) FROM curated.fact_daily_sales;"

# Check DAG errors
docker exec -it month1-airflow-webserver-1 bash -c "airflow dags list-import-errors"

# View Airflow logs
docker-compose logs airflow-webserver

# Stop everything
docker-compose stop
```

### Project Folder Structure
```
C:\de-training\month1\
├── docker-compose.yml
├── generate_realistic_data.py
├── generate_sample_data.py
├── dags\
│   └── retail_daily_ingestion.py
├── logs\
├── plugins\
└── init-db\
    └── 01_schema.sql
```
