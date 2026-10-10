import csv
import io
import os
import secrets

import psycopg
import reflex as rx

from warehouse_dashboard.data import (
    InventoryItem,
    OrderItem,
    PickBatchItem,
    ReportRow,
    get_dashboard_metrics,
    get_inventory,
    get_open_orders,
    get_pick_batches,
    get_report,
)

BACKGROUND = "#f6f8fb"
CARD = "#ffffff"
INK = "#172033"
MUTED = "#6b7280"
BORDER = "#e5e9f0"
BLUE = "#2563eb"
GREEN = "#16845b"
AMBER = "#b7791f"
RED = "#c24141"


class DashboardState(rx.State):
    authenticated: bool = False
    operator: str = ""
    login_username: str = ""
    login_password: str = ""
    login_error: str = ""
    active_view: str = "Overview"
    search: str = ""
    is_loading: bool = True
    data_error: str = ""
    open_orders: int = 0
    units_on_hand: int = 0
    replenishment_alerts: int = 0
    pick_accuracy: str = "0.0%"
    inventory_loading: bool = True
    inventory_error: str = ""
    inventory_items: list[InventoryItem] = []
    visible_inventory: list[InventoryItem] = []
    orders_loading: bool = True
    orders_error: str = ""
    orders: list[OrderItem] = []
    visible_orders: list[OrderItem] = []
    batches_loading: bool = True
    batches_error: str = ""
    batches: list[PickBatchItem] = []
    batch_capacity: int = 100
    report_name: str = "ABC slotting"
    report_loading: bool = False
    report_error: str = ""
    report_headers: list[str] = []
    report_rows: list[ReportRow] = []
    report_csv: str = ""
    last_updated: str = "Not loaded"

    def set_login_username(self, value: str) -> None:
        self.login_username = value
        self.login_error = ""

    def set_login_password(self, value: str) -> None:
        self.login_password = value
        self.login_error = ""

    def login(self) -> None:
        expected_username = os.getenv("WAREHOUSE_USERNAME")
        expected_password = os.getenv("WAREHOUSE_PASSWORD")
        if not expected_username or not expected_password:
            self.login_error = (
                "Authentication is not configured. Set WAREHOUSE_USERNAME and "
                "WAREHOUSE_PASSWORD."
            )
            return
        if not (
            secrets.compare_digest(self.login_username, expected_username)
            and secrets.compare_digest(self.login_password, expected_password)
        ):
            self.login_password = ""
            self.login_error = "Invalid username or password."
            return
        self.authenticated = True
        self.operator = self.login_username
        self.login_password = ""
        self.login_error = ""
        self.load_dashboard()

    def logout(self) -> None:
        self.authenticated = False
        self.operator = ""
        self.login_username = ""
        self.login_password = ""
        self.search = ""

    def select_view(self, view: str) -> None:
        self.active_view = view
        if view == "Reports" and not self.report_headers and not self.report_error:
            self.load_report()

    def set_search(self, value: str) -> None:
        self.search = value
        search = value.strip().lower()
        self.visible_inventory = [
            item
            for item in self.inventory_items
            if not search
            or search in item["sku"].lower()
            or search in item["description"].lower()
            or search in item["location"].lower()
        ]
        self.visible_orders = [
            order
            for order in self.orders
            if not search or search in order["order_id"].lower()
        ]

    def load_dashboard(self) -> None:
        self.is_loading = True
        self.data_error = ""
        try:
            metrics = get_dashboard_metrics(self.operator)
        except (OSError, RuntimeError, psycopg.Error) as exc:
            self.data_error = friendly_data_error(exc)
        else:
            self.open_orders = metrics["open_orders"]
            self.units_on_hand = metrics["units_on_hand"]
            self.replenishment_alerts = metrics["replenishment_alerts"]
            self.pick_accuracy = f"{metrics['pick_accuracy']:.1f}%"
        finally:
            self.is_loading = False
        self.last_updated = "Just now"
        self.load_inventory()

    def load_inventory(self) -> None:
        self.inventory_loading = True
        self.inventory_error = ""
        try:
            inventory = get_inventory(self.operator)
        except (OSError, RuntimeError, psycopg.Error) as exc:
            self.inventory_error = friendly_data_error(exc)
            self.inventory_items = []
            self.visible_inventory = []
        else:
            self.inventory_items = inventory
            self.visible_inventory = inventory
        finally:
            self.inventory_loading = False
        self.load_orders()
        self.load_batches()
        self.load_report()

    def load_orders(self) -> None:
        self.orders_loading = True
        self.orders_error = ""
        try:
            orders = get_open_orders(self.operator)
        except (OSError, RuntimeError, psycopg.Error) as exc:
            self.orders_error = friendly_data_error(exc)
            self.orders = []
            self.visible_orders = []
        else:
            self.orders = orders
            self.visible_orders = orders
        finally:
            self.orders_loading = False

    def load_batches(self) -> None:
        self.batches_loading = True
        self.batches_error = ""
        try:
            self.batches = get_pick_batches(self.batch_capacity, self.operator)
        except (OSError, RuntimeError, ValueError, psycopg.Error) as exc:
            self.batches_error = friendly_data_error(exc)
            self.batches = []
        finally:
            self.batches_loading = False

    def select_report(self, name: str) -> None:
        self.report_name = name
        self.load_report()

    def load_report(self) -> None:
        self.report_loading = True
        self.report_error = ""
        try:
            headers, rows = get_report(self.report_name, self.operator)
        except (OSError, RuntimeError, ValueError, psycopg.Error) as exc:
            self.report_error = friendly_data_error(exc)
            self.report_headers = []
            self.report_rows = []
            self.report_csv = ""
        else:
            self.report_headers = headers
            self.report_rows = rows
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(row["cells"] for row in rows)
            self.report_csv = output.getvalue()
        finally:
            self.report_loading = False

    def refresh(self) -> None:
        self.load_dashboard()


def friendly_data_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, RuntimeError) and str(exc):
        return str(exc)
    return (
        "Could not load live warehouse data. Check DATABASE_URL and database "
        "availability."
    )


def metric_card(
    label: str,
    value: str,
    detail: str,
    accent: str,
    trend: str,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.text(label, size="2", weight="medium", color=MUTED),
                rx.text(value, size="7", weight="bold", color=INK),
                rx.text(detail, size="1", color=MUTED),
                spacing="1",
                align="start",
            ),
            rx.box(
                rx.text(trend, size="2", weight="bold", color=accent),
                background=accent,
                opacity="0.12",
                border_radius="999px",
                padding_x="10px",
                padding_y="5px",
            ),
            justify="between",
            align="start",
            width="100%",
        ),
        background=CARD,
        border=f"1px solid {BORDER}",
        border_radius="14px",
        padding="20px",
        width="100%",
    )


def sidebar_item(label: str, marker: str) -> rx.Component:
    is_active = DashboardState.active_view == label
    return rx.button(
        rx.hstack(
            rx.box(
                rx.text(marker, size="1", weight="bold"),
                background=rx.cond(is_active, BLUE, "#eef2f7"),
                color=rx.cond(is_active, "white", MUTED),
                border_radius="6px",
                padding="6px",
            ),
            rx.text(label, size="2", weight=rx.cond(is_active, "bold", "medium")),
            spacing="3",
            align="center",
        ),
        on_click=DashboardState.select_view(label),
        background=rx.cond(is_active, "#eaf1ff", "transparent"),
        color=rx.cond(is_active, BLUE, MUTED),
        border="none",
        border_radius="9px",
        cursor="pointer",
        padding="9px 10px",
        width="100%",
        justify_content="start",
        _hover={"background": "#eaf1ff", "color": BLUE},
    )


def status_badge(label: str, color: str) -> rx.Component:
    return rx.text(
        label,
        size="1",
        weight="bold",
        color=color,
        background=f"{color}18",
        border_radius="999px",
        padding="4px 9px",
    )


def inventory_row(
    sku: str,
    description: str,
    location: str,
    on_hand: str,
    reorder_point: str,
    status: str,
    status_color: str,
) -> rx.Component:
    return rx.grid(
        rx.vstack(
            rx.text(sku, size="2", weight="bold", color=INK),
            rx.text(description, size="1", color=MUTED),
            align="start",
            spacing="1",
        ),
        rx.text(location, size="2", color=INK),
        rx.text(on_hand, size="2", color=INK),
        rx.text(reorder_point, size="2", color=INK),
        status_badge(status, status_color),
        columns="2fr 1fr 1fr 1fr 1fr",
        align="center",
        padding_y="14px",
        border_top=f"1px solid {BORDER}",
    )


def inventory_table() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text("Replenishment watchlist", size="4", weight="bold", color=INK),
                rx.text(
                    "SKUs approaching their reorder point",
                    size="2",
                    color=MUTED,
                ),
                align="start",
                spacing="1",
            ),
            rx.button(
                "View all inventory",
                variant="soft",
                color_scheme="blue",
                size="2",
                on_click=DashboardState.select_view("Inventory"),
            ),
            justify="between",
            align="center",
            width="100%",
            margin_bottom="14px",
        ),
        rx.grid(
            rx.text("SKU", size="1", weight="bold", color=MUTED),
            rx.text("Location", size="1", weight="bold", color=MUTED),
            rx.text("On hand", size="1", weight="bold", color=MUTED),
            rx.text("Reorder point", size="1", weight="bold", color=MUTED),
            rx.text("Status", size="1", weight="bold", color=MUTED),
            columns="2fr 1fr 1fr 1fr 1fr",
            padding_bottom="8px",
        ),
        inventory_row(
            "SKU-1048",
            "Corrugated carton 12 x 10",
            "A-03-02",
            "42 units",
            "50 units",
            "Reorder",
            AMBER,
        ),
        inventory_row(
            "SKU-2081",
            "Heavy-duty packing tape",
            "B-01-04",
            "18 units",
            "24 units",
            "Reorder",
            AMBER,
        ),
        inventory_row(
            "SKU-3310",
            "Pallet stretch wrap",
            "C-05-01",
            "96 units",
            "60 units",
            "Healthy",
            GREEN,
        ),
        background=CARD,
        border=f"1px solid {BORDER}",
        border_radius="14px",
        padding="20px",
        width="100%",
    )


def inventory_item_row(item: InventoryItem) -> rx.Component:
    return rx.grid(
        rx.vstack(
            rx.text(item["sku"], size="2", weight="bold", color=INK),
            rx.text(item["description"], size="1", color=MUTED),
            align="start",
            spacing="1",
        ),
        rx.text(item["location"], size="2", color=INK),
        rx.text(item["on_hand"], size="2", color=INK),
        rx.text(item["reorder_point"], size="2", color=INK),
        status_badge(
            item["status"],
            rx.cond(
                item["status"] == "Critical",
                RED,
                rx.cond(item["status"] == "Reorder", AMBER, GREEN),
            ),
        ),
        columns="2fr 1fr 1fr 1fr 1fr",
        align="center",
        padding_y="14px",
        border_top=f"1px solid {BORDER}",
    )


def inventory_view() -> rx.Component:
    return rx.vstack(
        rx.cond(
            DashboardState.inventory_loading,
            rx.callout(
                "Loading inventory from PostgreSQL...",
                icon="refresh-cw",
                color_scheme="blue",
            ),
            rx.cond(
                DashboardState.inventory_error != "",
                rx.callout(
                    DashboardState.inventory_error,
                    icon="triangle-alert",
                    color_scheme="amber",
                ),
                rx.fragment(),
            ),
        ),
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.text("Inventory", size="5", weight="bold", color=INK),
                    rx.text(
                        "Stock balances by SKU and warehouse location",
                        size="2",
                        color=MUTED,
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.text(
                    DashboardState.visible_inventory.length().to_string() + " records",
                    size="2",
                    color=MUTED,
                ),
                justify="between",
                align="center",
                width="100%",
                margin_bottom="18px",
            ),
            rx.grid(
                rx.text("SKU", size="1", weight="bold", color=MUTED),
                rx.text("Location", size="1", weight="bold", color=MUTED),
                rx.text("On hand", size="1", weight="bold", color=MUTED),
                rx.text("Reorder point", size="1", weight="bold", color=MUTED),
                rx.text("Status", size="1", weight="bold", color=MUTED),
                columns="2fr 1fr 1fr 1fr 1fr",
                padding_bottom="8px",
            ),
            rx.cond(
                DashboardState.visible_inventory.length() > 0,
                rx.foreach(DashboardState.visible_inventory, inventory_item_row),
                rx.text(
                    "No inventory records match your search.",
                    size="2",
                    color=MUTED,
                    padding_y="28px",
                ),
            ),
            background=CARD,
            border=f"1px solid {BORDER}",
            border_radius="14px",
            padding="20px",
            width="100%",
            overflow_x="auto",
        ),
        width="100%",
        spacing="4",
    )


def order_row(order: OrderItem) -> rx.Component:
    return rx.grid(
        rx.text(f"#{order['order_id']}", size="2", weight="bold", color=INK),
        rx.text(order["line_count"], size="2", color=INK),
        rx.text(order["units"], size="2", color=INK),
        status_badge(
            order["status"],
            rx.cond(order["status"] == "Ready", GREEN, AMBER),
        ),
        columns="2fr 1fr 1fr 1fr",
        align="center",
        padding_y="14px",
        border_top=f"1px solid {BORDER}",
    )


def orders_view() -> rx.Component:
    return rx.vstack(
        rx.cond(
            DashboardState.orders_loading,
            rx.callout(
                "Loading open orders from PostgreSQL...",
                icon="refresh-cw",
                color_scheme="blue",
            ),
            rx.cond(
                DashboardState.orders_error != "",
                rx.callout(
                    DashboardState.orders_error,
                    icon="triangle-alert",
                    color_scheme="amber",
                ),
                rx.fragment(),
            ),
        ),
        rx.box(
            rx.vstack(
                rx.text("Open orders", size="5", weight="bold", color=INK),
                rx.text(
                    "Orders with open pick lines, ready for warehouse execution",
                    size="2",
                    color=MUTED,
                ),
                align="start",
                spacing="1",
                margin_bottom="18px",
            ),
            rx.grid(
                rx.text("Order", size="1", weight="bold", color=MUTED),
                rx.text("Pick lines", size="1", weight="bold", color=MUTED),
                rx.text("Units", size="1", weight="bold", color=MUTED),
                rx.text("Status", size="1", weight="bold", color=MUTED),
                columns="2fr 1fr 1fr 1fr",
                padding_bottom="8px",
            ),
            rx.cond(
                DashboardState.visible_orders.length() > 0,
                rx.foreach(DashboardState.visible_orders, order_row),
                rx.text(
                    "No open orders match your search.",
                    size="2",
                    color=MUTED,
                    padding_y="28px",
                ),
            ),
            background=CARD,
            border=f"1px solid {BORDER}",
            border_radius="14px",
            padding="20px",
            width="100%",
            overflow_x="auto",
        ),
        width="100%",
        spacing="4",
    )


def batch_row(batch: PickBatchItem) -> rx.Component:
    return rx.grid(
        rx.text(batch["batch_id"], size="2", weight="bold", color=BLUE),
        rx.text(f"#{batch['order_id']}", size="2", color=INK),
        rx.text(batch["sku"], size="2", color=INK),
        rx.text(batch["location"], size="2", color=INK),
        rx.text(batch["zone"], size="2", color=INK),
        rx.text(batch["quantity"], size="2", color=INK),
        rx.text(batch["batch_units"], size="2", color=INK),
        columns="1.1fr 1fr 1.1fr 1.1fr 0.7fr 1fr 1fr",
        align="center",
        padding_y="12px",
        border_top=f"1px solid {BORDER}",
    )


def picking_view() -> rx.Component:
    return rx.vstack(
        rx.cond(
            DashboardState.batches_loading,
            rx.callout(
                "Building pick batches from open lines...",
                icon="refresh-cw",
                color_scheme="blue",
            ),
            rx.cond(
                DashboardState.batches_error != "",
                rx.callout(
                    DashboardState.batches_error,
                    icon="triangle-alert",
                    color_scheme="amber",
                ),
                rx.fragment(),
            ),
        ),
        rx.box(
            rx.vstack(
                rx.text("Picking plan", size="5", weight="bold", color=INK),
                rx.text(
                    "Complete orders grouped into walking-order batches",
                    size="2",
                    color=MUTED,
                ),
                align="start",
                spacing="1",
                margin_bottom="18px",
            ),
            rx.grid(
                rx.text("Batch", size="1", weight="bold", color=MUTED),
                rx.text("Order", size="1", weight="bold", color=MUTED),
                rx.text("SKU", size="1", weight="bold", color=MUTED),
                rx.text("Location", size="1", weight="bold", color=MUTED),
                rx.text("Zone", size="1", weight="bold", color=MUTED),
                rx.text("Quantity", size="1", weight="bold", color=MUTED),
                rx.text("Batch total", size="1", weight="bold", color=MUTED),
                columns="1.1fr 1fr 1.1fr 1.1fr 0.7fr 1fr 1fr",
                padding_bottom="8px",
            ),
            rx.cond(
                DashboardState.batches.length() > 0,
                rx.foreach(DashboardState.batches, batch_row),
                rx.text(
                    "No open pick lines are ready for batching.",
                    size="2",
                    color=MUTED,
                    padding_y="28px",
                ),
            ),
            background=CARD,
            border=f"1px solid {BORDER}",
            border_radius="14px",
            padding="20px",
            width="100%",
            overflow_x="auto",
        ),
        width="100%",
        spacing="4",
    )


def report_view() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Reports", size="5", weight="bold", color=INK),
                rx.text(
                    "Run reviewed operational reports against PostgreSQL",
                    size="2",
                    color=MUTED,
                ),
                align="start",
                spacing="1",
            ),
            rx.select(
                ["ABC slotting", "Inventory accuracy"],
                value=DashboardState.report_name,
                on_change=DashboardState.select_report,
                width="220px",
            ),
            rx.button(
                "Download CSV",
                variant="soft",
                color_scheme="blue",
                on_click=rx.download(
                    data=DashboardState.report_csv,
                    filename="warehouse-report.csv",
                    mime_type="text/csv",
                ),
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        rx.cond(
            DashboardState.report_loading,
            rx.callout(
                "Running report...",
                icon="refresh-cw",
                color_scheme="blue",
            ),
            rx.cond(
                DashboardState.report_error != "",
                rx.callout(
                    DashboardState.report_error,
                    icon="triangle-alert",
                    color_scheme="amber",
                ),
                rx.fragment(),
            ),
        ),
        rx.box(
            rx.cond(
                DashboardState.report_rows.length() > 0,
                rx.vstack(
                    rx.text(
                        DashboardState.report_rows.length().to_string()
                        + " result rows",
                        size="2",
                        color=MUTED,
                        align_self="end",
                    ),
                    rx.grid(
                        rx.foreach(
                            DashboardState.report_headers,
                            lambda header: rx.text(
                                header,
                                size="1",
                                weight="bold",
                                color=MUTED,
                            ),
                        ),
                        columns="repeat(auto-fit, minmax(120px, 1fr))",
                        padding_bottom="8px",
                    ),
                    rx.foreach(
                        DashboardState.report_rows,
                        lambda row: rx.grid(
                            rx.foreach(
                                row["cells"],
                                lambda cell: rx.text(cell, size="2", color=INK),
                            ),
                            columns="repeat(auto-fit, minmax(120px, 1fr))",
                            align="center",
                            padding_y="12px",
                            border_top=f"1px solid {BORDER}",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                rx.text(
                    "No results were returned for this report.",
                    size="2",
                    color=MUTED,
                    padding_y="28px",
                ),
            ),
            background=CARD,
            border=f"1px solid {BORDER}",
            border_radius="14px",
            padding="20px",
            width="100%",
            overflow_x="auto",
        ),
        width="100%",
        spacing="4",
    )


def pick_activity() -> rx.Component:
    activities = [
        ("Batch #1042", "12 orders · Zone A", "Ready", GREEN),
        ("Batch #1041", "8 orders · Zone C", "In progress", BLUE),
        ("Batch #1040", "15 orders · Zone B", "Completed", MUTED),
    ]
    return rx.box(
        rx.vstack(
            rx.text("Picking activity", size="4", weight="bold", color=INK),
            rx.text("Today’s warehouse execution", size="2", color=MUTED),
            align="start",
            spacing="1",
            margin_bottom="14px",
        ),
        rx.vstack(
            *[
                rx.hstack(
                    rx.box(
                        rx.text(
                            batch.split("#")[1], size="2", weight="bold", color=BLUE
                        ),
                        background="#eaf1ff",
                        border_radius="8px",
                        padding="9px",
                    ),
                    rx.vstack(
                        rx.text(batch, size="2", weight="bold", color=INK),
                        rx.text(detail, size="1", color=MUTED),
                        align="start",
                        spacing="1",
                    ),
                    status_badge(status, color),
                    justify="between",
                    align="center",
                    width="100%",
                    padding_y="10px",
                    border_top=f"1px solid {BORDER}",
                )
                for batch, detail, status, color in activities
            ],
            spacing="0",
        ),
        background=CARD,
        border=f"1px solid {BORDER}",
        border_radius="14px",
        padding="20px",
        width="100%",
    )


def overview() -> rx.Component:
    return rx.vstack(
        rx.cond(
            DashboardState.is_loading,
            rx.callout(
                "Loading live warehouse metrics...",
                icon="refresh-cw",
                color_scheme="blue",
            ),
            rx.cond(
                DashboardState.data_error != "",
                rx.callout(
                    DashboardState.data_error,
                    icon="triangle-alert",
                    color_scheme="amber",
                ),
                rx.fragment(),
            ),
        ),
        rx.grid(
            metric_card(
                "Open orders",
                DashboardState.open_orders.to_string(),
                "Live from PostgreSQL",
                BLUE,
                "LIVE",
            ),
            metric_card(
                "Units on hand",
                DashboardState.units_on_hand.to_string(),
                "Across current stock",
                GREEN,
                "LIVE",
            ),
            metric_card(
                "Replenishment alerts",
                DashboardState.replenishment_alerts.to_string(),
                "Based on 30-day demand",
                AMBER,
                "LIVE",
            ),
            metric_card(
                "Pick accuracy",
                DashboardState.pick_accuracy,
                "Last 30 days",
                GREEN,
                "LIVE",
            ),
            columns=rx.breakpoints(initial="1", sm="2", lg="4"),
            spacing="4",
            width="100%",
        ),
        rx.grid(
            inventory_table(),
            pick_activity(),
            columns=rx.breakpoints(initial="1", lg="1.65fr 1fr"),
            spacing="4",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


def placeholder_view(title: str, description: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, size="6", weight="bold", color=INK),
            rx.text(description, size="3", color=MUTED),
            rx.button(
                "Return to overview",
                on_click=DashboardState.select_view("Overview"),
                color_scheme="blue",
            ),
            align="center",
            spacing="4",
            padding="80px 20px",
        ),
        background=CARD,
        border=f"1px solid {BORDER}",
        border_radius="14px",
        width="100%",
    )


def content() -> rx.Component:
    return rx.cond(
        DashboardState.active_view == "Overview",
        overview(),
        rx.cond(
            DashboardState.active_view == "Inventory",
            inventory_view(),
            rx.cond(
                DashboardState.active_view == "Orders",
                orders_view(),
                rx.cond(
                    DashboardState.active_view == "Picking",
                    picking_view(),
                    report_view(),
                ),
            ),
        ),
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.text("W", size="4", weight="bold", color="white"),
                    background=BLUE,
                    border_radius="9px",
                    padding="8px 11px",
                ),
                rx.vstack(
                    rx.text("Warehouse", size="3", weight="bold", color=INK),
                    rx.text("Operations", size="1", color=MUTED),
                    align="start",
                    spacing="0",
                ),
                spacing="3",
                align="center",
                margin_bottom="34px",
            ),
            rx.text("WORKSPACE", size="1", weight="bold", color="#9aa3b2"),
            rx.vstack(
                sidebar_item("Overview", "O"),
                sidebar_item("Inventory", "I"),
                sidebar_item("Orders", "O"),
                sidebar_item("Picking", "P"),
                sidebar_item("Reports", "R"),
                spacing="1",
                width="100%",
            ),
            rx.spacer(),
            rx.box(
                rx.vstack(
                    rx.text("Need help?", size="2", weight="bold", color=INK),
                    rx.text(
                        "Review the operations guide for warehouse workflows.",
                        size="1",
                        color=MUTED,
                    ),
                    rx.button("Open guide", variant="soft", size="1", width="100%"),
                    align="start",
                    spacing="2",
                ),
                background="#f1f5ff",
                border_radius="10px",
                padding="14px",
                width="100%",
            ),
            height="100%",
            align="start",
            width="100%",
        ),
        background=CARD,
        border_right=f"1px solid {BORDER}",
        min_width="238px",
        padding="26px 18px",
        height="100vh",
        position="sticky",
        top="0",
    )


def header() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(DashboardState.active_view, size="6", weight="bold", color=INK),
            rx.text(
                "Keep inventory moving and orders on schedule.",
                size="2",
                color=MUTED,
            ),
            align="start",
            spacing="1",
        ),
        rx.hstack(
            rx.input(
                placeholder="Search SKU or order",
                value=DashboardState.search,
                on_change=DashboardState.set_search,
                width="210px",
                size="2",
            ),
            rx.button(
                "Refresh",
                variant="soft",
                color_scheme="blue",
                on_click=DashboardState.refresh,
            ),
            rx.button(
                "Export report",
                variant="soft",
                color_scheme="blue",
                on_click=rx.download(
                    data=DashboardState.report_csv,
                    filename="warehouse-report.csv",
                    mime_type="text/csv",
                ),
            ),
            rx.box(
                rx.text(
                    DashboardState.operator,
                    size="2",
                    weight="bold",
                    color=BLUE,
                ),
                background="#eaf1ff",
                border_radius="999px",
                padding="9px",
            ),
            rx.button(
                "Sign out",
                variant="ghost",
                color_scheme="gray",
                on_click=DashboardState.logout,
            ),
            spacing="3",
            align="center",
            wrap="wrap",
        ),
        justify="between",
        align="center",
        width="100%",
        margin_bottom="26px",
    )


def login_view() -> rx.Component:
    return rx.center(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.text("W", size="4", weight="bold", color="white"),
                        background=BLUE,
                        border_radius="9px",
                        padding="8px 11px",
                    ),
                    rx.vstack(
                        rx.text("Warehouse", size="4", weight="bold", color=INK),
                        rx.text("Operations portal", size="2", color=MUTED),
                        align="start",
                        spacing="0",
                    ),
                    spacing="3",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Sign in", size="6", weight="bold", color=INK),
                    rx.text(
                        "Use your warehouse operator account to continue.",
                        size="2",
                        color=MUTED,
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.input(
                    placeholder="Username",
                    value=DashboardState.login_username,
                    on_change=DashboardState.set_login_username,
                    width="100%",
                ),
                rx.input(
                    placeholder="Password",
                    type="password",
                    value=DashboardState.login_password,
                    on_change=DashboardState.set_login_password,
                    width="100%",
                ),
                rx.cond(
                    DashboardState.login_error != "",
                    rx.callout(
                        DashboardState.login_error,
                        icon="triangle-alert",
                        color_scheme="amber",
                    ),
                    rx.fragment(),
                ),
                rx.button(
                    "Sign in",
                    on_click=DashboardState.login,
                    color_scheme="blue",
                    width="100%",
                ),
                align="stretch",
                spacing="4",
            ),
            background=CARD,
            border=f"1px solid {BORDER}",
            border_radius="16px",
            box_shadow="0 12px 40px rgba(23, 32, 51, 0.08)",
            padding="34px",
            width="min(420px, 92vw)",
        ),
        background=BACKGROUND,
        min_height="100vh",
        width="100%",
    )


def application_view() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            header(),
            content(),
            padding="34px 40px",
            width="100%",
            min_height="100vh",
        ),
        spacing="0",
        align="start",
        background=BACKGROUND,
        min_height="100vh",
        width="100%",
    )


def index() -> rx.Component:
    return rx.cond(
        DashboardState.authenticated,
        application_view(),
        login_view(),
    )


app = rx.App()
app.add_page(index, title="Warehouse Operations")
