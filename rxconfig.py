import reflex as rx

config = rx.Config(
    app_name="warehouse_dashboard",
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="blue",
                radius="medium",
            )
        )
    ],
)
