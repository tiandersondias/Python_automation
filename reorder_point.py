import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg


REORDER_POINTS_SQL = (
    Path(__file__).resolve().parent / "sql" / "reorder_points.sql"
).read_text()


def calculate_reorder_points(
    conn: psycopg.Connection, service_level_z: float = 1.65
) -> pd.DataFrame:
    if service_level_z <= 0:
        raise ValueError("service_level_z must be greater than zero")

    df = pd.read_sql_query(
        REORDER_POINTS_SQL,
        conn,
    )
    columns = [
        "sku",
        "mean",
        "std",
        "lead_time_days",
        "safety",
        "reorder_pt",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    if df["lead_time_days"].isna().any() or (df["lead_time_days"] < 0).any():
        raise ValueError("lead_time_days must be nonnegative for every SKU")

    grouped = df.groupby(["sku", "lead_time_days"], as_index=False)["qty"].agg(
        mean="mean", std="std"
    )
    grouped["std"] = grouped["std"].fillna(0)
    grouped["safety"] = (
        service_level_z
        * grouped["std"]
        * np.sqrt(grouped["lead_time_days"])
    )
    grouped["reorder_pt"] = (
        grouped["mean"] * grouped["lead_time_days"] + grouped["safety"]
    )
    return grouped[columns]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate inventory reorder points from daily demand."
    )
    parser.add_argument(
        "database_url",
        nargs="?",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL (default: DATABASE_URL environment variable)",
    )
    args = parser.parse_args()

    if not args.database_url:
        parser.error("provide database_url or set the DATABASE_URL environment variable")

    with psycopg.connect(args.database_url) as conn:
        result = calculate_reorder_points(conn)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()