import pandas as pd

import batch_picking


def test_get_open_pick_batches_returns_query_result(monkeypatch):
    expected = pd.DataFrame(
        [
            {
                "pick_sequence": 10,
                "zone": "A",
                "location_id": "A-03-02",
                "orders": 2,
                "lines": 3,
                "units": 7,
            }
        ]
    )
    monkeypatch.setattr(
        batch_picking.pd,
        "read_sql_query",
        lambda *_args: expected,
    )

    result = batch_picking.get_open_pick_batches(object())

    pd.testing.assert_frame_equal(result, expected)
