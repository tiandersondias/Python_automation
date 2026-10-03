import pandas as pd
import pytest

import batch_picking


def test_get_open_pick_batches_assigns_complete_orders(monkeypatch):
    open_lines = pd.DataFrame(
        [
            {
                "order_id": 1,
                "pick_sequence": 10,
                "zone": "A",
                "location_id": "A-03-02",
                "qty": 60,
            },
            {
                "order_id": 1,
                "pick_sequence": 20,
                "zone": "B",
                "location_id": "B-01-01",
                "qty": 10,
            },
            {
                "order_id": 2,
                "pick_sequence": 10,
                "zone": "A",
                "location_id": "A-03-02",
                "qty": 30,
            },
        ]
    )
    monkeypatch.setattr(
        batch_picking,
        "read_query_dataframe",
        lambda *_args: open_lines,
    )

    result = batch_picking.get_open_pick_batches(object(), max_units=100)

    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame(
            [
                {
                    "batch_id": 1,
                    "pick_sequence": 10,
                    "zone": "A",
                    "location_id": "A-03-02",
                    "orders": 2,
                    "lines": 2,
                    "units": 90,
                },
                {
                    "batch_id": 1,
                    "pick_sequence": 20,
                    "zone": "B",
                    "location_id": "B-01-01",
                    "orders": 1,
                    "lines": 1,
                    "units": 10,
                },
            ]
        ),
    )


def test_build_pick_batches_rejects_oversized_orders():
    lines = pd.DataFrame(
        [
            {
                "order_id": 1,
                "pick_sequence": 1,
                "zone": "A",
                "location_id": "A-1",
                "qty": 101,
            }
        ]
    )

    with pytest.raises(ValueError, match="exceed max_units"):
        batch_picking.build_pick_batches(lines, max_units=100)
