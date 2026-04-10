-- Challenge File: "Target: PostgreSQL database (staging + curated layers)"
-- Challenge File, Source Schema section — matching all 3 source files

-- =============================================
-- STAGING LAYER — raw copies, no transformation
-- =============================================
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.sales_transactions (
    transaction_id    VARCHAR(50),
    store_id          VARCHAR(50),
    product_id        VARCHAR(50),
    quantity          INTEGER,
    unit_price        NUMERIC(10,2),
    discount_pct      NUMERIC(5,2),
    transaction_date  DATE,
    payment_method    VARCHAR(50),
    customer_id       VARCHAR(50)  -- Challenge File: "nullable"
);

CREATE TABLE IF NOT EXISTS staging.product_catalog (
    product_id    VARCHAR(50),
    product_name  VARCHAR(255),
    category      VARCHAR(100),
    subcategory   VARCHAR(100),
    brand         VARCHAR(100),
    cost_price    NUMERIC(10,2),
    list_price    NUMERIC(10,2),
    supplier_id   VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS staging.store_locations (
    store_id      VARCHAR(50),
    store_name    VARCHAR(255),
    city          VARCHAR(100),
    state         VARCHAR(100),
    region        VARCHAR(100),
    store_type    VARCHAR(50),
    opening_date  DATE
);

-- =============================================
-- CURATED LAYER — transformed, business-ready
-- =============================================
CREATE SCHEMA IF NOT EXISTS curated;

-- Challenge File, Transformation section: "Load (upsert into curated.fact_daily_sales)"
CREATE TABLE IF NOT EXISTS curated.fact_daily_sales (
    store_id          VARCHAR(50),
    product_id        VARCHAR(50),
    transaction_date  DATE,
    category          VARCHAR(100),
    subcategory       VARCHAR(100),
    brand             VARCHAR(100),
    total_quantity    INTEGER,
    total_revenue     NUMERIC(12,2),
    total_tax         NUMERIC(12,2),
    transaction_count INTEGER,
    avg_discount      NUMERIC(5,2),
    load_timestamp    TIMESTAMP,
    PRIMARY KEY (store_id, product_id, transaction_date)
);

-- Error/dead-letter table for bad rows
-- Challenge File, Error Handling: "Error row handling: log bad rows to error table"
CREATE TABLE IF NOT EXISTS staging.error_log (
    error_id       SERIAL PRIMARY KEY,
    source_table   VARCHAR(100),
    raw_data       TEXT,
    error_message  TEXT,
    logged_at      TIMESTAMP DEFAULT NOW()
);

-- Intermediate staging table for load_curated PostgresOperator
-- transform_sales writes here, load_curated UPSERTs from here
CREATE TABLE IF NOT EXISTS staging.fact_daily_sales_stage (
    store_id          VARCHAR(50),
    product_id        VARCHAR(50),
    transaction_date  DATE,
    category          VARCHAR(100),
    subcategory       VARCHAR(100),
    brand             VARCHAR(100),
    total_quantity    INTEGER,
    total_revenue     NUMERIC(12,2),
    total_tax         NUMERIC(12,2),
    transaction_count INTEGER,
    avg_discount      NUMERIC(5,2),
    load_timestamp    TIMESTAMP
);