import os
from pathlib import Path
from typing import TypedDict

import psycopg


class DashboardMetrics(TypedDict):
    open_orders: int
    units_on_hand: int
    replenishment_alerts: int
    pick_accuracy: float


class InventoryItem(TypedDict):
    sku: str
    description: str
    location: str
    on_hand: str
    reorder_point: str
    status: str


class OrderItem(TypedDict):
    order_id: str
    line_count: str
    units: str
    status: str


class PickBatchItem(TypedDict):
    batch_id: str
    order_id: str
    sku: str
    location: str
    zone: str
    quantity: str
    batch_units: str


class ReportRow(TypedDict):
    cells: list[str]


DASHBOARD_METRICS_SQL = """
WITH recent_demand AS (
    SELECT
        sku,
        AVG(qty) AS average_daily_demand
    FROM daily_demand
    WHERE day >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY sku
),
inventory AS (
    SELECT
        st.sku,
        st.system_qty,
        COALESCE(rd.average_daily_demand, 0) * s.lead_time_days
            AS reorder_point
    FROM stock AS st
    JOIN sku AS s USING (sku)
    LEFT JOIN recent_demand AS rd USING (sku)
)
SELECT
    (SELECT COUNT(*) FROM orders WHERE status = 'OPEN')::int AS open_orders,
    (SELECT COALESCE(SUM(system_qty), 0) FROM stock)::int AS units_on_hand,
    (
        SELECT COUNT(*)
        FROM inventory
        WHERE system_qty <= reorder_point
    )::int AS replenishment_alerts,
    COALESCE(
        100.0 * COUNT(*) FILTER (WHERE status = 'PICKED')
        / NULLIF(COUNT(*) FILTER (WHERE status IN ('PICKED', 'SHORT')), 0),
        0
    )::float AS pick_accuracy
FROM pick_lines
WHERE pick_date >= CURRENT_DATE - INTERVAL '30 days';
"""


def get_dashboard_metrics() -> DashboardMetrics:
    """Read the overview metrics from PostgreSQL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(DASHBOARD_METRICS_SQL)
            row = cursor.fetchone()

    if row is None:
        raise RuntimeError("The dashboard metrics query returned no data")

    return {
        "open_orders": int(row[0] or 0),
        "units_on_hand": int(row[1] or 0),
        "replenishment_alerts": int(row[2] or 0),
        "pick_accuracy": float(row[3] or 0),
    }


INVENTORY_SQL = """
WITH recent_demand AS (
    SELECT
        sku,
        AVG(qty) AS average_daily_demand
    FROM daily_demand
    WHERE day >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY sku
)
SELECT
    st.sku,
    s.description,
    st.location_id,
    st.system_qty,
    COALESCE(rd.average_daily_demand, 0) * s.lead_time_days AS reorder_point
FROM stock AS st
JOIN sku AS s USING (sku)
LEFT JOIN recent_demand AS rd USING (sku)
ORDER BY st.system_qty - (
    COALESCE(rd.average_daily_demand, 0) * s.lead_time_days
), st.sku, st.location_id;
"""


def get_inventory() -> list[InventoryItem]:
    """Read stock balances and calculated reorder points from PostgreSQL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(INVENTORY_SQL)
            rows = cursor.fetchall()

    inventory: list[InventoryItem] = []
    for sku, description, location, on_hand, reorder_point in rows:
        on_hand_value = int(on_hand or 0)
        reorder_point_value = float(reorder_point or 0)
        if on_hand_value == 0:
            status = "Critical"
        elif on_hand_value <= reorder_point_value:
            status = "Reorder"
        else:
            status = "Healthy"
        inventory.append(
            {
                "sku": str(sku),
                "description": str(description),
                "location": str(location),
                "on_hand": f"{on_hand_value} units",
                "reorder_point": f"{reorder_point_value:.1f} units",
                "status": status,
            }
        )
    return inventory


ORDERS_SQL = """
SELECT
    o.order_id,
    COUNT(p.pick_line_id) AS line_count,
    COALESCE(SUM(p.qty), 0) AS units
FROM orders AS o
LEFT JOIN pick_lines AS p
    ON p.order_id = o.order_id AND p.status = 'OPEN'
WHERE o.status = 'OPEN'
GROUP BY o.order_id
ORDER BY o.created_at, o.order_id;
"""


OPEN_PICK_LINES_SQL = """
SELECT
    p.order_id,
    p.sku,
    p.location_id,
    l.zone,
    p.qty
FROM pick_lines AS p
JOIN location AS l USING (location_id)
JOIN orders AS o USING (order_id)
WHERE p.status = 'OPEN' AND o.status = 'OPEN'
ORDER BY p.order_id, l.zone, l.pick_sequence, p.location_id;
"""


def _connect() -> psycopg.Connection:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(database_url)


def get_open_orders() -> list[OrderItem]:
    """Read open orders and their current open pick-line totals."""
    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(ORDERS_SQL)
            rows = cursor.fetchall()
    return [
        {
            "order_id": str(order_id),
            "line_count": f"{int(line_count or 0)} lines",
            "units": f"{int(units or 0)} units",
            "status": "Ready" if line_count else "No open lines",
        }
        for order_id, line_count, units in rows
    ]


def get_pick_batches(max_units: int = 100) -> list[PickBatchItem]:
    """Build complete-order picking batches from open PostgreSQL pick lines."""
    if max_units <= 0:
        raise ValueError("max_units must be greater than zero")

    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(OPEN_PICK_LINES_SQL)
            rows = cursor.fetchall()

    orders: dict[int, int] = {}
    for order_id, _sku, _location, _zone, quantity in rows:
        orders[order_id] = orders.get(order_id, 0) + int(quantity)
    oversized = [order_id for order_id, units in orders.items() if units > max_units]
    if oversized:
        raise ValueError(
            "Orders exceed batch capacity: "
            + ", ".join(str(order_id) for order_id in oversized)
        )

    order_batches: dict[int, int] = {}
    batch_id = 1
    batch_units = 0
    for order_id, units in orders.items():
        if batch_units and batch_units + units > max_units:
            batch_id += 1
            batch_units = 0
        order_batches[order_id] = batch_id
        batch_units += units

    batch_totals: dict[int, int] = {}
    for order_id, units in orders.items():
        batch_totals[order_batches[order_id]] = (
            batch_totals.get(order_batches[order_id], 0) + units
        )

    return [
        {
            "batch_id": f"Batch {order_batches[order_id]}",
            "order_id": str(order_id),
            "sku": str(sku),
            "location": str(location),
            "zone": str(zone),
            "quantity": f"{int(quantity)} units",
            "batch_units": f"{batch_totals[order_batches[order_id]]} units",
        }
        for order_id, sku, location, zone, quantity in rows
    ]


REPORT_SQL = {
    "ABC slotting": (
        Path(__file__).resolve().parent.parent / "sql" / "abc_slotting.sql"
    ),
    "Inventory accuracy": (
        Path(__file__).resolve().parent.parent / "sql" / "inventory_accuracy_checks.sql"
    ),
}


def get_report(name: str) -> tuple[list[str], list[ReportRow]]:
    """Execute one of the reviewed SQL reports and format its result."""
    try:
        report_path = REPORT_SQL[name]
    except KeyError as exc:
        raise ValueError(f"Unknown report: {name}") from exc

    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(report_path.read_text())
            rows = cursor.fetchall()
            headers = [column.name for column in cursor.description or ()]

    return headers, [
        {"cells": [str(value) if value is not None else "—" for value in row]}
        for row in rows
    ]
