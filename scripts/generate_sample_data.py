# generate_sample_data.py
# Uploads 3 pipe-delimited CSVs to MinIO
# Challenge File: "Format: CSV with headers, pipe-delimited"
# Challenge File: "Source: MinIO bucket (daily CSV exports from POS system)"

import boto3
import pandas as pd
import io
from botocore.exceptions import ClientError

from datetime import date, timedelta
RUN_DATE = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Generating sample data for: {RUN_DATE}")
BUCKET    = "raw-data"
ENDPOINT  = "http://localhost:9000"

s3 = boto3.client(
    "s3",
    endpoint_url         = ENDPOINT,
    aws_access_key_id    = "minioadmin",
    aws_secret_access_key= "minioadmin",
)

# --- Create bucket ---
try:
    s3.create_bucket(Bucket=BUCKET)
    print(f"✔ Bucket '{BUCKET}' created.")
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
        print(f"✔ Bucket '{BUCKET}' already exists — skipping.")
    else:
        raise

def upload_df(df, key):
    """Upload DataFrame as pipe-delimited CSV to MinIO.
    Challenge File: 'Format: CSV with headers, pipe-delimited'
    """
    buf = io.StringIO()
    df.to_csv(buf, sep="|", index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"✔ Uploaded: {key}  ({len(df)} rows)")

# -----------------------------------------------
# 1. sales_transactions.csv
# Challenge File, Source Schema: sales_transactions fields
# Volume: "~500K rows/day" — using 100 rows for local dev
# -----------------------------------------------
sales = pd.DataFrame({
    "transaction_id":   [f"TXN{i:06d}" for i in range(1, 101)],
    "store_id":         [f"STR{(i % 5) + 1:03d}" for i in range(100)],
    "product_id":       [f"PRD{(i % 20) + 1:04d}" for i in range(100)],
    "quantity":         [max(1, i % 10) for i in range(100)],
    "unit_price":       [round(10 + (i % 50) * 1.5, 2) for i in range(100)],
    "discount_pct":     [round((i % 20) * 0.5, 2) for i in range(100)],
    "transaction_date": [RUN_DATE] * 100,
    "payment_method":   ["CARD" if i % 2 == 0 else "CASH" for i in range(100)],
    # Challenge File: "customer_id (string, nullable)"
    "customer_id":      [f"CUST{i:05d}" if i % 5 != 0 else None for i in range(100)],
})
upload_df(sales, f"retail-data/{RUN_DATE}/sales_transactions.csv")

# -----------------------------------------------
# 2. product_catalog.csv
# Challenge File, Source Schema: product_catalog fields
# -----------------------------------------------
products = pd.DataFrame({
    "product_id":   [f"PRD{i:04d}" for i in range(1, 21)],
    "product_name": [f"Product {i}" for i in range(1, 21)],
    "category":     [["Electronics","Clothing","Food","Home"][i % 4] for i in range(20)],
    "subcategory":  [f"Sub{i % 5}" for i in range(20)],
    "brand":        [f"Brand{i % 4}" for i in range(20)],
    "cost_price":   [round(5 + i * 2.5, 2) for i in range(20)],
    "list_price":   [round(10 + i * 4.0, 2) for i in range(20)],
    "supplier_id":  [f"SUP{i % 3 + 1:03d}" for i in range(20)],
})
upload_df(products, f"retail-data/{RUN_DATE}/product_catalog.csv")

# -----------------------------------------------
# 3. store_locations.csv
# Challenge File, Source Schema: store_locations fields
# -----------------------------------------------
stores = pd.DataFrame({
    "store_id":     [f"STR{i:03d}" for i in range(1, 6)],
    "store_name":   [f"RetailCo Store {i}" for i in range(1, 6)],
    "city":         ["Colombo", "Kandy", "Galle", "Jaffna", "Negombo"],
    "state":        ["Western", "Central", "Southern", "Northern", "Western"],
    "region":       ["South", "Central", "South", "North", "South"],
    "store_type":   ["Flagship", "Standard", "Standard", "Kiosk", "Standard"],
    "opening_date": ["2020-01-15","2019-06-01","2021-03-10","2022-07-20","2018-11-05"],
})
upload_df(stores, f"retail-data/{RUN_DATE}/store_locations.csv")

print(f"\n✔ All 3 files uploaded to s3://{BUCKET}/retail-data/{RUN_DATE}/")
print("Verify at: http://localhost:9001")