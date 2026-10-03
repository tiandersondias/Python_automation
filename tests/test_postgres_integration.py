from pathlib import Path

import pandas as pd

import batch_picking
import reorder_point


SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def run_sql_file(conn, filename):
    return conn.execute((SQL_DIR / filename).read_text()).fetchall()


def seed_database(conn):
    conn.executemany(
        "INSERT INTO sku (sku, description, lead_time_days) VALUES (%s, %s, %s)",
        [
            ("FAST", "Fast mover", 2),
            ("SLOW", "Slow mover", 7),
            ("COUNTED", "Counted item", 5),
        ],
    )
    conn.executemany(
        """
        INSERT INTO location
            (location_id, zone, aisle, bay, level, pick_sequence)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [
            ("A-01-01", "A", 1, 1, 1, 10),
            ("B-01-01", "B", 1, 1, 1, 20),
        ],
    )
    conn.executemany(
        "INSERT INTO orders (order_id) VALUES (%s)",
        [(1001,), (1002,)],
    )
    conn.executemany(
        """
        INSERT INTO pick_lines
            (order_id, sku, location_id, qty, status, pick_date, picked_by, picked_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE - INTERVAL '10 days',
                %s, CASE WHEN %s = 'PICKED' THEN CURRENT_TIMESTAMP ELSE NULL END)
        """,
        [
            (1001, "FAST", "A-01-01", 80, "PICKED", "worker", "PICKED"),
            (1001, "SLOW", "B-01-01", 10, "PICKED", "worker", "PICKED"),
            (1002, "FAST", "A-01-01", 5, "OPEN", None, "OPEN"),
        ],
    )
    conn.executemany(
        "INSERT INTO daily_demand (sku, day, qty) VALUES (%s, CURRENT_DATE, %s)",
        [("FAST", 10), ("SLOW", 4)],
    )
    conn.executemany(
        "INSERT INTO stock (sku, location_id, system_qty) VALUES (%s, %s, %s)",
        [("COUNTED", "A-01-01", 10)],
    )
    conn.executemany(
        """
        INSERT INTO cycle_counts
            (sku, location_id, counted_qty, counted_by)
        VALUES (%s, %s, %s, %s)
        """,
        [
            ("COUNTED", "A-01-01", 9, "worker"),
        ],
    )
    conn.execute(
        """
        INSERT INTO cycle_counts
            (sku, location_id, counted_qty, counted_by, counted_at)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP - INTERVAL '1 day')
        """,
        ("COUNTED", "A-01-01", 8, "older-worker"),
    )
    conn.commit()


def test_postgres_schema_and_reports(postgres_connection):
    seed_database(postgres_connection)

    abc_rows = run_sql_file(postgres_connection, "abc_slotting.sql")
    assert abc_rows == [("FAST", 80, 88.89, "A"), ("SLOW", 10, 100.0, "B/C")]

    batch_rows = run_sql_file(postgres_connection, "batch_picking_by_zone.sql")
    assert batch_rows == [(10, "A", "A-01-01", 1, 1, 5)]

    accuracy_rows = run_sql_file(
        postgres_connection, "inventory_accuracy_checks.sql"
    )
    assert accuracy_rows[0][0:5] == ("COUNTED", "A-01-01", 10, 9, -1)
    assert len(accuracy_rows) == 1

    reorder_rows = reorder_point.calculate_reorder_points(postgres_connection)
    assert list(reorder_rows["sku"]) == ["FAST", "SLOW"]
    assert list(reorder_rows["lead_time_days"]) == [2, 7]

    batch_frame = batch_picking.get_open_pick_batches(postgres_connection)
    pd.testing.assert_frame_equal(
        batch_frame,
        pd.DataFrame(
            [
                {
                    "pick_sequence": 10,
                    "zone": "A",
                    "location_id": "A-01-01",
                    "orders": 1,
                    "lines": 1,
                    "units": 5,
                }
            ]
        ),
    )
