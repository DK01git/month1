# FILE: filter_transform.py
# PURPOSE: Filter invalid rows from sales transactions
# Called from: transform_sales PythonOperator in DAG

import logging
import pandas as pd

log = logging.getLogger(__name__)


def apply_filter(df: pd.DataFrame, pg_hook) -> pd.DataFrame:
    """
    Remove invalid rows from sales transactions DataFrame.
    Invalid rows are written to staging.error_log before removal.

    Rules:
      - transaction_id must not be null
      - quantity must be > 0
      - unit_price must be > 0

    Args:
        df:       Raw sales DataFrame from staging
        pg_hook:  PostgresHook for error_log writes

    Returns:
        Filtered DataFrame with only valid rows
    """
    before = len(df)

    # Identify bad rows BEFORE filtering
    bad_mask = ~(
        df["transaction_id"].notna() &
        (df["quantity"].astype(float) > 0) &
        (df["unit_price"].astype(float) > 0)
    )
    bad_rows = df[bad_mask].copy()

    # Write bad rows to staging.error_log
    # Challenge File, Part 4: "Error row handling: log bad rows to error table"
    if not bad_rows.empty:
        error_rows = []
        for _, bad_row in bad_rows.iterrows():
            error_rows.append((
                "staging.sales_transactions",
                bad_row.to_json(),
                "Failed filter: null transaction_id "
                "or quantity/unit_price <= 0",
            ))
        pg_hook.insert_rows(
            table="staging.error_log",
            rows=error_rows,
            target_fields=["source_table", "raw_data", "error_message"],
        )
        log.warning(
            "Wrote %d invalid rows to staging.error_log",
            len(bad_rows)
        )

    # Apply filter — keep only valid rows
    filtered_df = df[~bad_mask].copy()
    removed = before - len(filtered_df)

    log.info(
        "Filter transform: %d input rows → %d valid rows "
        "(%d removed)", before, len(filtered_df), removed
    )
    return filtered_df