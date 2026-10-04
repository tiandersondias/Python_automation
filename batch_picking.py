import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg

from database import read_query_dataframe
from observability import configure_logging, utc_now
from operations import log_report_failure

OPEN_PICK_LINES_SQL = (
    Path(__file__).resolve().parent / "sql" / "open_pick_lines.sql"
).read_text()


def build_pick_batches(pick_lines: pd.DataFrame, max_units: int = 100) -> pd.DataFrame:
    """Assign complete orders to capacity-limited, executable batches."""
    output_columns = [
        "batch_id",
        "order_id",
        "pick_line_id",
        "sku",
        "pick_sequence",
        "zone",
        "location_id",
        "qty",
        "batch_units",
    ]
    if max_units <= 0:
        raise ValueError("max_units must be greater than zero")
    if pick_lines.empty:
        return pd.DataFrame(columns=output_columns)

    order_units = pick_lines.groupby("order_id", sort=True)["qty"].sum()
    oversized = order_units[order_units > max_units]
    if not oversized.empty:
        raise ValueError(
            "orders exceed max_units and cannot be kept complete: "
            + ", ".join(str(order_id) for order_id in oversized.index)
        )

    order_batch = {}
    batch_id = 1
    batch_units = 0
    for order_id, units in order_units.items():
        if batch_units and batch_units + units > max_units:
            batch_id += 1
            batch_units = 0
        order_batch[order_id] = batch_id
        batch_units += units

    planned = pick_lines.copy()
    planned["batch_id"] = planned["order_id"].map(order_batch)
    planned["batch_units"] = planned.groupby("batch_id")["qty"].transform("sum")
    return planned.sort_values(
        ["batch_id", "zone", "pick_sequence", "location_id", "order_id"]
    )[output_columns].reset_index(drop=True)


def get_open_pick_batches(
    conn: psycopg.Connection, max_units: int = 100
) -> pd.DataFrame:
    """Return executable pick-line details grouped into complete orders."""
    pick_lines = read_query_dataframe(conn, OPEN_PICK_LINES_SQL)
    return build_pick_batches(pick_lines, max_units=max_units)


def main() -> None:
    logger = configure_logging()
    parser = argparse.ArgumentParser(
        description="Build a walking-order batch plan for open pick lines."
    )
    parser.add_argument(
        "database_url",
        nargs="?",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL (default: DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--output-format",
        choices=("table", "csv", "json"),
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--max-units",
        type=int,
        default=100,
        help="Maximum units per batch; orders remain complete (default: 100)",
    )
    args = parser.parse_args()

    if not args.database_url:
        parser.error(
            "provide database_url or set the DATABASE_URL environment variable"
        )
    if args.max_units <= 0:
        parser.error("--max-units must be greater than zero")

    try:
        with psycopg.connect(args.database_url) as conn:
            logger.info(
                "report=batch_picking generated_at=%s max_units=%s output_format=%s",
                utc_now(),
                args.max_units,
                args.output_format,
            )
            batches = get_open_pick_batches(conn, max_units=args.max_units)
    except psycopg.errors.UndefinedTable as exc:
        logger.error("report=batch_picking failure=incomplete_schema")
        log_report_failure(logger, "batch_picking", exc)
        print(
            "Database schema is incomplete: apply the project migrations first.",
            file=sys.stderr,
        )
        print(f"Details: {exc.diag.message_primary}", file=sys.stderr)
        raise SystemExit(1) from exc
    except psycopg.Error as exc:
        logger.error("report=batch_picking failure=database_error")
        log_report_failure(logger, "batch_picking", exc)
        print(
            "Could not connect to or query PostgreSQL. Check DATABASE_URL and "
            "database availability.",
            file=sys.stderr,
        )
        print(f"Details: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if args.output_format == "csv":
        print(batches.to_csv(index=False), end="")
    elif args.output_format == "json":
        print(batches.to_json(orient="records"))
    else:
        print(batches.to_string(index=False))


if __name__ == "__main__":
    main()
