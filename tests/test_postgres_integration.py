from decimal import Decimal
from pathlib import Path

import pandas as pd

import batch_picking
import migrate
import reorder_point

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def run_sql_file(conn, filename):
    return conn.execute((SQL_DIR / filename).read_text()).fetchall()


def seed_database(conn):
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO sku (sku, description, lead_time_days) VALUES (%s, %s, %s)",
            [
                ("FAST", "Fast mover", 2),
                ("SLOW", "Slow mover", 7),
                ("COUNTED", "Counted item", 5),
            ],
        )
        cur.executemany(
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
        cur.executemany(
            "INSERT INTO orders (order_id) VALUES (%s)",
            [(1001,), (1002,)],
        )
        cur.executemany(
            """
            INSERT INTO pick_lines
                (order_id, sku, location_id, qty, status, pick_date,
                 picked_by, picked_at)
            VALUES (%s, %s, %s, %s, %s,
                    CASE WHEN %s = 'OPEN' THEN NULL
                         ELSE CURRENT_DATE - INTERVAL '10 days' END,
                    %s, CASE WHEN %s = 'PICKED' THEN CURRENT_TIMESTAMP ELSE NULL END)
            """,
            [
                (1001, "FAST", "A-01-01", 80, "PICKED", "PICKED", "worker", "PICKED"),
                (1001, "SLOW", "B-01-01", 10, "PICKED", "PICKED", "worker", "PICKED"),
                (1002, "FAST", "A-01-01", 5, "OPEN", "OPEN", None, "OPEN"),
            ],
        )
        cur.executemany(
            "INSERT INTO daily_demand (sku, day, qty) VALUES (%s, CURRENT_DATE, %s)",
            [("FAST", 10), ("SLOW", 4)],
        )
        cur.executemany(
            "INSERT INTO stock (sku, location_id, system_qty) VALUES (%s, %s, %s)",
            [("COUNTED", "A-01-01", 10)],
        )
        cur.executemany(
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
    assert abc_rows == [
        ("FAST", 80, Decimal("88.89"), "A"),
        ("SLOW", 10, Decimal("100.00"), "B/C"),
    ]

    batch_rows = run_sql_file(postgres_connection, "batch_picking_by_zone.sql")
    assert batch_rows == [
        (1002, 10, "A", "A-01-01", 1, 5),
    ]

    accuracy_rows = run_sql_file(postgres_connection, "inventory_accuracy_checks.sql")
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
                    "batch_id": 1,
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

    postgres_connection.execute(
        "SELECT set_config('app.user', 'integration-test', true)"
    )
    postgres_connection.execute(
        "UPDATE pick_lines SET status = 'PICKED', pick_date = CURRENT_DATE, "
        "picked_by = 'worker', picked_at = CURRENT_TIMESTAMP WHERE order_id = 1002"
    )
    postgres_connection.execute(
        "UPDATE stock SET system_qty = 8 "
        "WHERE sku = 'COUNTED' AND location_id = 'A-01-01'"
    )
    postgres_connection.commit()
    assert postgres_connection.execute(
        "SELECT old_status, new_status, changed_by FROM pick_line_status_history"
    ).fetchall() == [("OPEN", "PICKED", "integration-test")]
    assert postgres_connection.execute(
        "SELECT old_system_qty, new_system_qty, changed_by "
        "FROM stock_adjustment_history"
    ).fetchall() == [(10, 8, "integration-test")]


def test_failed_migration_rolls_back_completely(postgres_connection, tmp_path):
    migration = tmp_path / "005_intentionally_fails.sql"
    migration.write_text(
        """
        CREATE TABLE should_be_rolled_back (id INT);
        SELECT definitely_missing_function();
        """
    )

    try:
        migrate.apply_migrations(postgres_connection, migrations_dir=tmp_path)
    except Exception:
        postgres_connection.rollback()
    else:
        raise AssertionError("failed migration unexpectedly succeeded")

    assert (
        postgres_connection.execute(
            "SELECT to_regclass(current_schema() || '.should_be_rolled_back')"
        ).fetchone()[0]
        is None
    )
    assert (
        postgres_connection.execute(
            "SELECT version FROM schema_migrations WHERE version = '005'"
        ).fetchone()
        is None
    )


def test_out_of_order_migration_is_rejected(postgres_connection, tmp_path):
    postgres_connection.execute(
        """
        INSERT INTO schema_migrations (version, name)
        VALUES ('006', 'future_migration.sql')
        """
    )
    postgres_connection.commit()
    migration = tmp_path / "005_out_of_order.sql"
    migration.write_text("SELECT 1;")

    try:
        migrate.apply_migrations(postgres_connection, migrations_dir=tmp_path)
    except RuntimeError as exc:
        postgres_connection.rollback()
        assert "out of order" in str(exc)
    else:
        raise AssertionError("out-of-order migration unexpectedly succeeded")
