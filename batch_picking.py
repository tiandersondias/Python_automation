import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg


OPEN_PICK_BATCHES_SQL = (
    Path(__file__).resolve().parent / "sql" / "batch_picking_by_zone.sql"
).read_text()


def get_open_pick_batches(conn: psycopg.Connection) -> pd.DataFrame:
    """Return an open-pick batch plan ordered by the warehouse walking route."""
    return pd.read_sql_query(
        OPEN_PICK_BATCHES_SQL,
        conn,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a walking-order batch plan for open pick lines."
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
        batches = get_open_pick_batches(conn)
    print(batches.to_string(index=False))


if __name__ == "__main__":
    main()
