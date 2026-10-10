import reflex as rx

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
    active_view: str = "Overview"
    search: str = ""

    def select_view(self, view: str) -> None:
        self.active_view = view

    def set_search(self, value: str) -> None:
        self.search = value


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
        rx.grid(
            metric_card("Open orders", "128", "23 due before 2 PM", BLUE, "+8.4%"),
            metric_card("Units on hand", "24,680", "Across 312 SKUs", GREEN, "+3.1%"),
            metric_card(
                "Replenishment alerts", "12", "4 critical items", AMBER, "-2 today"
            ),
            metric_card("Pick accuracy", "98.6%", "Last 30 days", GREEN, "+1.2%"),
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
            placeholder_view(
                "Inventory",
                "Inventory drill-down is ready for the PostgreSQL reporting layer.",
            ),
            rx.cond(
                DashboardState.active_view == "Orders",
                placeholder_view(
                    "Orders",
                    "Order queue and fulfillment details will live here.",
                ),
                placeholder_view(
                    "Reports",
                    "Operational reports will be connected to the existing "
                    "SQL utilities.",
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
            rx.button("Export report", variant="soft", color_scheme="blue"),
            rx.box(
                rx.text("TA", size="2", weight="bold", color=BLUE),
                background="#eaf1ff",
                border_radius="999px",
                padding="9px",
            ),
            spacing="3",
            align="center",
        ),
        justify="between",
        align="center",
        width="100%",
        margin_bottom="26px",
    )


def index() -> rx.Component:
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


app = rx.App()
app.add_page(index, title="Warehouse Operations")
