"""Populate a local warehouse database with repeatable demonstration data."""

import argparse
import os
import sys
from datetime import date, datetime, timedelta

import psycopg

DEMO_SKUS = ("DEMO-100", "DEMO-200", "DEMO-300", "DEMO-400", "DEMO-500")
DEMO_LOCATIONS = ("DEMO-A01", "DEMO-A02", "DEMO-B01", "DEMO-C01")
DEMO_ORDERS = (9000001, 9000002, 9000003, 9000004)
DEMO_DATABASE_USER = "mock-seed"


def seed_database(database_url: str) -> None:
    today = date.today()
    picked_at = datetime.now().replace(microsecond=0)

    skus = [
        ("DEMO-100", "Corrugated carton 12 x 10", 4.25, 5),
        ("DEMO-200", "Heavy-duty packing tape", 8.50, 4),
        ("DEMO-300", "Pallet stretch wrap", 15.75, 7),
        ("DEMO-400", "Shipping labels 4 x 6", 12.00, 3),
        ("DEMO-500", "Protective foam sheets", 6.20, 6),
    ]
    locations = [
        ("DEMO-A01", "A", 1, 1, 1, 10),
        ("DEMO-A02", "A", 1, 2, 1, 20),
        ("DEMO-B01", "B", 2, 1, 1, 30),
        ("DEMO-C01", "C", 3, 1, 1, 40),
    ]
    stock = [
        ("DEMO-100", "DEMO-A01", 12),
        ("DEMO-200", "DEMO-A02", 6),
        ("DEMO-300", "DEMO-B01", 84),
        ("DEMO-400", "DEMO-C01", 28),
        ("DEMO-500", "DEMO-C01", 0),
    ]

    with psycopg.connect(database_url) as conn:
        conn.execute("SELECT set_config('app.user', %s, true)", (DEMO_DATABASE_USER,))
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM daily_demand WHERE sku = ANY(%s)", (list(DEMO_SKUS),)
            )
            cursor.execute(
                "DELETE FROM cycle_counts WHERE sku = ANY(%s)", (list(DEMO_SKUS),)
            )
            cursor.execute(
                "DELETE FROM pick_lines WHERE order_id = ANY(%s)",
                (list(DEMO_ORDERS),),
            )
            cursor.execute(
                "DELETE FROM orders WHERE order_id = ANY(%s)", (list(DEMO_ORDERS),)
            )
            cursor.execute("DELETE FROM stock WHERE sku = ANY(%s)", (list(DEMO_SKUS),))
            cursor.execute(
                "DELETE FROM location WHERE location_id = ANY(%s)",
                (list(DEMO_LOCATIONS),),
            )
            cursor.execute("DELETE FROM sku WHERE sku = ANY(%s)", (list(DEMO_SKUS),))

            cursor.executemany(
                """
                INSERT INTO sku (sku, description, unit_cost, lead_time_days)
                VALUES (%s, %s, %s, %s)
                """,
                skus,
            )
            cursor.executemany(
                """
                INSERT INTO location
                    (location_id, zone, aisle, bay, level, pick_sequence)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                locations,
            )
            cursor.executemany(
                """
                INSERT INTO stock (sku, location_id, system_qty)
                VALUES (%s, %s, %s)
                """,
                stock,
            )

            demand_rows = []
            demand_rates = {
                "DEMO-100": 8,
                "DEMO-200": 5,
                "DEMO-300": 3,
                "DEMO-400": 2,
                "DEMO-500": 4,
            }
            for sku, rate in demand_rates.items():
                for days_ago in range(1, 31):
                    demand_rows.append((sku, today - timedelta(days=days_ago), rate))
            cursor.executemany(
                "INSERT INTO daily_demand (sku, day, qty) VALUES (%s, %s, %s)",
                demand_rows,
            )

            cursor.executemany(
                "INSERT INTO orders (order_id, status) VALUES (%s, %s)",
                [
                    (9000001, "OPEN"),
                    (9000002, "OPEN"),
                    (9000003, "OPEN"),
                    (9000004, "CLOSED"),
                ],
            )
            cursor.executemany(
                """
                INSERT INTO pick_lines
                    (order_id, sku, location_id, qty, status,
                     pick_date, picked_by, picked_at, short_reason, short_qty)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        9000001,
                        "DEMO-100",
                        "DEMO-A01",
                        6,
                        "OPEN",
                        None,
                        None,
                        None,
                        None,
                        None,
                    ),
                    (
                        9000001,
                        "DEMO-200",
                        "DEMO-A02",
                        2,
                        "OPEN",
                        None,
                        None,
                        None,
                        None,
                        None,
                    ),
                    (
                        9000002,
                        "DEMO-300",
                        "DEMO-B01",
                        5,
                        "OPEN",
                        None,
                        None,
                        None,
                        None,
                        None,
                    ),
                    (
                        9000002,
                        "DEMO-500",
                        "DEMO-C01",
                        3,
                        "OPEN",
                        None,
                        None,
                        None,
                        None,
                        None,
                    ),
                    (
                        9000003,
                        "DEMO-400",
                        "DEMO-C01",
                        4,
                        "OPEN",
                        None,
                        None,
                        None,
                        None,
                        None,
                    ),
                    (
                        9000004,
                        "DEMO-100",
                        "DEMO-A01",
                        12,
                        "PICKED",
                        today - timedelta(days=2),
                        "operator",
                        picked_at,
                        None,
                        None,
                    ),
                    (
                        9000004,
                        "DEMO-200",
                        "DEMO-A02",
                        8,
                        "PICKED",
                        today - timedelta(days=3),
                        "operator",
                        picked_at,
                        None,
                        None,
                    ),
                    (
                        9000004,
                        "DEMO-500",
                        "DEMO-C01",
                        5,
                        "SHORT",
                        today - timedelta(days=1),
                        "operator",
                        picked_at,
                        "Damaged stock",
                        2,
                    ),
                ],
            )

            cursor.executemany(
                """
                INSERT INTO cycle_counts
                    (sku, location_id, counted_qty, counted_by)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    ("DEMO-100", "DEMO-A01", 10, "operator"),
                    ("DEMO-200", "DEMO-A02", 8, "operator"),
                    ("DEMO-300", "DEMO-B01", 84, "operator"),
                    ("DEMO-400", "DEMO-C01", 27, "operator"),
                    ("DEMO-500", "DEMO-C01", 0, "operator"),
                ],
            )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate PostgreSQL with repeatable warehouse demo data."
    )
    parser.add_argument(
        "database_url",
        nargs="?",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL (default: DATABASE_URL)",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("provide database_url or set DATABASE_URL")

    try:
        seed_database(args.database_url)
    except psycopg.Error as exc:
        print(f"Mock data seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("Mock warehouse data loaded successfully.")
    print("Demo SKUs: " + ", ".join(DEMO_SKUS))
    print("Demo orders: " + ", ".join(str(order) for order in DEMO_ORDERS))


if __name__ == "__main__":
    main()
