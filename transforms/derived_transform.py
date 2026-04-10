# FILE: derived_transform.py
# PURPOSE: Calculate derived columns on sales transactions
# Called from: transform_sales PythonOperator in DAG

import logging
import pandas as pd

log = logging.getLogger(__name__)


def apply_derived_columns(df: pd.DataFrame, run_date: str) -> pd.DataFrame:
    """
    Add calculated columns to sales DataFrame.

    Derived columns (Challenge File, Part 3):
      - line_total     = quantity * unit_price * (1 - discount_pct / 100)
      - tax_amount     = line_total * 0.08
      - total_with_tax = line_total + tax_amount
      - load_timestamp = current timestamp
      - source_file    = source filename with run date

    Args:
        df:       Filtered sales DataFrame
        run_date: Execution date string YYYY-MM-DD

    Returns:
        DataFrame with derived columns added
    """
    df = df.copy()

    # Cast numeric columns explicitly
    # Prevents silent string arithmetic errors from CSV import
    df["quantity"]     = df["quantity"].astype(int)
    df["unit_price"]   = df["unit_price"].astype(float)
    df["discount_pct"] = df["discount_pct"].astype(float)

    # Challenge File, Part 3: "Derived Column Transform"
    df["line_total"] = (
        df["quantity"] * df["unit_price"] * (1 - df["discount_pct"] / 100)
    ).round(2)

    df["tax_amount"]     = (df["line_total"] * 0.08).round(2)
    df["total_with_tax"] = (df["line_total"] + df["tax_amount"]).round(2)
    df["load_timestamp"] = pd.Timestamp.now()
    df["source_file"]    = f"sales_transactions_{run_date}.csv"

    log.info(
        "Derived transform: added line_total, tax_amount, "
        "total_with_tax, load_timestamp, source_file"
    )
    return df