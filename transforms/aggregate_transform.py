# =============================================================
# FILE: aggregate_transform.py
# PURPOSE: Aggregate sales to daily store-product summaries
# Challenge File, Part 3: "Aggregate Transform"
# Called from: transform_sales PythonOperator in DAG
# =============================================================

import logging
import pandas as pd

log = logging.getLogger(__name__)


def apply_aggregation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate sales transactions to daily store-product level.

    Aggregation (Challenge File, Part 3):
      GROUP BY store_id, product_id, transaction_date
      - total_quantity    = SUM(quantity)
      - total_revenue     = SUM(line_total)
      - total_tax         = SUM(tax_amount)
      - transaction_count = COUNT(transaction_id)
      - avg_discount      = AVG(discount_pct)

    Args:
        df: DataFrame with derived columns applied

    Returns:
        Aggregated DataFrame at store-product-date grain
    """
    # Challenge File, Part 3: "Aggregate Transform"
    daily_summary = df.groupby(
        ["store_id", "product_id", "transaction_date"]
    ).agg(
        total_quantity   =("quantity",      "sum"),
        total_revenue    =("line_total",    "sum"),
        total_tax        =("tax_amount",    "sum"),
        transaction_count=("transaction_id","count"),
        avg_discount     =("discount_pct",  "mean"),
    ).reset_index()

    # Round numeric columns
    daily_summary["total_revenue"] = daily_summary["total_revenue"].round(2)
    daily_summary["total_tax"]     = daily_summary["total_tax"].round(2)
    daily_summary["avg_discount"]  = daily_summary["avg_discount"].round(2)
    daily_summary["load_timestamp"]= pd.Timestamp.now()

    log.info(
        "Aggregate transform: %d transactions → "
        "%d store-product-date rows",
        len(df), len(daily_summary)
    )
    return daily_summary