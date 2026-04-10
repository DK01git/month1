# generate_realistic_data.py
# Generates realistic-scale sample data for Month 1 pipeline submission
# sales_transactions: 10,000 rows
# product_catalog:       200 rows
# store_locations:        50 rows
# Challenge File: "Format: CSV with headers, pipe-delimited"

import boto3
import io
import random
from botocore.exceptions import ClientError
from datetime import date, timedelta

import pandas as pd
import numpy as np

# ---------------------------------------------------
# Config
# ---------------------------------------------------
RUN_DATE = "2026-04-07"
BUCKET    = "raw-data"
ENDPOINT  = "http://localhost:9000"

print(f"Generating realistic data for: {RUN_DATE}")

random.seed(42)
np.random.seed(42)

s3 = boto3.client(
    "s3",
    endpoint_url          = ENDPOINT,
    aws_access_key_id     = "minioadmin",
    aws_secret_access_key = "minioadmin",
)

# Create bucket if needed
try:
    s3.create_bucket(Bucket=BUCKET)
    print(f"✔ Bucket '{BUCKET}' created.")
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
        print(f"✔ Bucket '{BUCKET}' already exists.")
    else:
        raise

def upload_df(df, key):
    buf = io.StringIO()
    # Challenge File: "Format: CSV with headers, pipe-delimited"
    df.to_csv(buf, sep="|", index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"✔ Uploaded: {key}  ({len(df):,} rows)")

# ---------------------------------------------------
# 1. store_locations.csv — 50 stores
# Challenge File, Source Schema: store_locations fields
# ---------------------------------------------------
CITIES = [
    ("Colombo",    "Western",   "South"),
    ("Kandy",      "Central",   "Central"),
    ("Galle",      "Southern",  "South"),
    ("Jaffna",     "Northern",  "North"),
    ("Negombo",    "Western",   "South"),
    ("Matara",     "Southern",  "South"),
    ("Kurunegala", "North Western", "West"),
    ("Anuradhapura","North Central","North"),
    ("Ratnapura",  "Sabaragamuwa","Central"),
    ("Badulla",    "Uva",       "Central"),
]
STORE_TYPES = ["Flagship", "Standard", "Kiosk", "Express", "Warehouse"]

stores_data = []
for i in range(1, 51):
    city_data = CITIES[i % len(CITIES)]
    opening   = date(2015, 1, 1) + timedelta(days=random.randint(0, 2920))
    stores_data.append({
        "store_id":     f"STR{i:03d}",
        "store_name":   f"RetailCo {city_data[0]} {i}",
        "city":         city_data[0],
        "state":        city_data[1],
        "region":       city_data[2],
        "store_type":   STORE_TYPES[i % len(STORE_TYPES)],
        "opening_date": opening.strftime("%Y-%m-%d"),
    })

stores_df = pd.DataFrame(stores_data)
upload_df(stores_df, f"retail-data/{RUN_DATE}/store_locations.csv")

# ---------------------------------------------------
# 2. product_catalog.csv — 200 products
# Challenge File, Source Schema: product_catalog fields
# ---------------------------------------------------
CATEGORIES = {
    "Electronics": ["Phones",    "Laptops",    "Accessories", "Audio"],
    "Clothing":    ["Men",       "Women",      "Kids",        "Sports"],
    "Food":        ["Beverages", "Snacks",     "Fresh",       "Frozen"],
    "Home":        ["Furniture", "Appliances", "Decor",       "Garden"],
    "Health":      ["Pharmacy",  "Beauty",     "Fitness",     "Wellness"],
}
BRANDS = [
    "Samsung", "Apple",   "Nike",    "Adidas",  "Unilever",
    "Nestlé",  "IKEA",    "Philips", "Haier",   "LocalBrand",
]
SUPPLIERS = [f"SUP{i:03d}" for i in range(1, 21)]

products_data = []
for i in range(1, 201):
    cat        = list(CATEGORIES.keys())[i % len(CATEGORIES)]
    subcats    = CATEGORIES[cat]
    subcat     = subcats[i % len(subcats)]
    cost       = round(random.uniform(5, 500), 2)
    list_price = round(cost * random.uniform(1.3, 2.5), 2)
    products_data.append({
        "product_id":   f"PRD{i:04d}",
        "product_name": f"{subcat} Item {i}",
        "category":     cat,
        "subcategory":  subcat,
        "brand":        BRANDS[i % len(BRANDS)],
        "cost_price":   cost,
        "list_price":   list_price,
        "supplier_id":  SUPPLIERS[i % len(SUPPLIERS)],
    })

products_df = pd.DataFrame(products_data)
upload_df(products_df, f"retail-data/{RUN_DATE}/product_catalog.csv")

# ---------------------------------------------------
# 3. sales_transactions.csv — 10,000 rows
# Challenge File, Source Schema: sales_transactions fields
# Challenge File: "~500K rows/day" — using 10K for local dev
# ---------------------------------------------------
PAYMENT_METHODS = ["CARD", "CASH", "DIGITAL_WALLET", "CREDIT"]

# Introduce intentional bad rows to test error_log
# 50 bad rows out of 10,050 total — ~0.5% error rate
TOTAL_ROWS   = 10_000
BAD_ROWS     = 50

transactions_data = []

# Good rows
for i in range(1, TOTAL_ROWS + 1):
    store_id   = f"STR{random.randint(1, 50):03d}"
    product_id = f"PRD{random.randint(1, 200):04d}"
    quantity   = random.randint(1, 20)
    unit_price = round(random.uniform(10, 1000), 2)
    discount   = round(random.choice([0, 0, 0, 5, 10, 15, 20, 25]), 2)
    customer   = (
        f"CUST{random.randint(1, 50000):05d}"
        if random.random() > 0.15  # 15% anonymous
        else None
    )
    transactions_data.append({
        "transaction_id":   f"TXN{i:07d}",
        "store_id":         store_id,
        "product_id":       product_id,
        "quantity":         quantity,
        "unit_price":       unit_price,
        "discount_pct":     discount,
        "transaction_date": RUN_DATE,
        "payment_method":   random.choice(PAYMENT_METHODS),
        "customer_id":      customer,
    })

# Bad rows — intentional invalids to test error_log
# Challenge File, Part 4: "Error row handling: log bad rows to error table"
for j in range(BAD_ROWS):
    bad_type = j % 3
    if bad_type == 0:
        # Null transaction_id
        transactions_data.append({
            "transaction_id":   None,
            "store_id":         f"STR{random.randint(1,50):03d}",
            "product_id":       f"PRD{random.randint(1,200):04d}",
            "quantity":         random.randint(1, 5),
            "unit_price":       round(random.uniform(10, 100), 2),
            "discount_pct":     0,
            "transaction_date": RUN_DATE,
            "payment_method":   "CARD",
            "customer_id":      None,
        })
    elif bad_type == 1:
        # Zero quantity
        transactions_data.append({
            "transaction_id":   f"TXNBAD{j:04d}",
            "store_id":         f"STR{random.randint(1,50):03d}",
            "product_id":       f"PRD{random.randint(1,200):04d}",
            "quantity":         0,   # ← invalid
            "unit_price":       round(random.uniform(10, 100), 2),
            "discount_pct":     0,
            "transaction_date": RUN_DATE,
            "payment_method":   "CASH",
            "customer_id":      None,
        })
    else:
        # Negative unit price
        transactions_data.append({
            "transaction_id":   f"TXNBAD{j:04d}",
            "store_id":         f"STR{random.randint(1,50):03d}",
            "product_id":       f"PRD{random.randint(1,200):04d}",
            "quantity":         random.randint(1, 5),
            "unit_price":       -99.99,   # ← invalid
            "discount_pct":     0,
            "transaction_date": RUN_DATE,
            "payment_method":   "CARD",
            "customer_id":      None,
        })

# Shuffle so bad rows aren't all at the end
random.shuffle(transactions_data)

sales_df = pd.DataFrame(transactions_data)
upload_df(sales_df, f"retail-data/{RUN_DATE}/sales_transactions.csv")

# ---------------------------------------------------
# Summary
# ---------------------------------------------------
print(f"""
Summary:
  store_locations:     {len(stores_df):>6,} rows
  product_catalog:     {len(products_df):>6,} rows
  sales_transactions:  {len(sales_df):>6,} rows
    └── valid rows:    {TOTAL_ROWS:>6,}
    └── bad rows:      {BAD_ROWS:>6,} (intentional — tests error_log)

Run date: {RUN_DATE}
Verify at: http://localhost:9001
""")