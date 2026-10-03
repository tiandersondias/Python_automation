import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg

from database import read_query_dataframe
from observability import configure_logging, utc_now
from operations import log_report_failure

REORDER_POINTS_SQL = (
    Path(__file__).resolve().parent / "sql" / "reorder_points.sql"
).read_text()


def calculate_reorder_points(
    conn: psycopg.Connection, service_level_z: float = 1.65
) -> pd.DataFrame:
    if service_level_z <= 0:
        raise ValueError("service_level_z must be greater than zero")

    df = read_query_dataframe(
        conn,
        REORDER_POINTS_SQL,
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
        service_level_z * grouped["std"] * np.sqrt(grouped["lead_time_days"])
    )
    grouped["reorder_pt"] = (
        grouped["mean"] * grouped["lead_time_days"] + grouped["safety"]
    )
    return grouped[columns]


def main() -> None:
    logger = configure_logging()
    parser = argparse.ArgumentParser(
        description="Calculate inventory reorder points from daily demand."
    )
    parser.add_argument(
        "database_url",
        nargs="?",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL (default: DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--service-level-z",
        type=float,
        default=1.65,
        help="Safety-stock z-score (default: 1.65, approximately 95%% service)",
    )
    parser.add_argument(
        "--output-format",
        choices=("table", "csv", "json"),
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    if not args.database_url:
        parser.error(
            "provide database_url or set the DATABASE_URL environment variable"
        )
    if args.service_level_z <= 0:
        parser.error("--service-level-z must be greater than zero")

    try:
        with psycopg.connect(args.database_url) as conn:
            logger.info(
                "report=reorder_points generated_at=%s service_level_z=%s "
                "output_format=%s",
                utc_now(),
                args.service_level_z,
                args.output_format,
            )
            result = calculate_reorder_points(
                conn, service_level_z=args.service_level_z
            )
    except psycopg.errors.UndefinedTable as exc:
        logger.error("report=reorder_points failure=incomplete_schema")
        log_report_failure(logger, "reorder_points", exc)
        print(
            "Database schema is incomplete: apply the project migrations first.",
            file=sys.stderr,
        )
        print(f"Details: {exc.diag.message_primary}", file=sys.stderr)
        raise SystemExit(1) from exc
    except psycopg.Error as exc:
        logger.error("report=reorder_points failure=database_error")
        log_report_failure(logger, "reorder_points", exc)
        print(
            "Could not connect to or query PostgreSQL. Check DATABASE_URL and "
            "database availability.",
            file=sys.stderr,
        )
        print(f"Details: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if args.output_format == "csv":
        print(result.to_csv(index=False), end="")
    elif args.output_format == "json":
        print(result.to_json(orient="records"))
    else:
        print(result.to_string(index=False))


if __name__ == "__main__":
    main()
