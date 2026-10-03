import pandas as pd
import pytest

import reorder_point


def test_calculate_reorder_points_uses_per_sku_lead_times(monkeypatch):
    demand = pd.DataFrame(
        {
            "sku": ["A", "A", "B"],
            "day": ["2026-10-01", "2026-10-02", "2026-10-01"],
            "qty": [10, 14, 4],
            "lead_time_days": [2, 2, 7],
        }
    )
    monkeypatch.setattr(reorder_point.pd, "read_sql_query", lambda *_args: demand)

    result = reorder_point.calculate_reorder_points(object())

    assert list(result["sku"]) == ["A", "B"]
    assert list(result["lead_time_days"]) == [2, 7]
    assert result.loc[result["sku"] == "B", "reorder_pt"].iloc[0] == 28


def test_calculate_reorder_points_returns_empty_schema(monkeypatch):
    monkeypatch.setattr(
        reorder_point.pd,
        "read_sql_query",
        lambda *_args: pd.DataFrame(
            columns=["sku", "day", "qty", "lead_time_days"]
        ),
    )

    result = reorder_point.calculate_reorder_points(object())

    assert result.empty
    assert list(result.columns) == [
        "sku",
        "mean",
        "std",
        "lead_time_days",
        "safety",
        "reorder_pt",
    ]


def test_calculate_reorder_points_rejects_invalid_inputs(monkeypatch):
    with pytest.raises(ValueError, match="service_level_z"):
        reorder_point.calculate_reorder_points(object(), service_level_z=0)

    demand = pd.DataFrame(
        {
            "sku": ["A"],
            "day": ["2026-10-01"],
            "qty": [10],
            "lead_time_days": [-1],
        }
    )
    monkeypatch.setattr(reorder_point.pd, "read_sql_query", lambda *_args: demand)

    with pytest.raises(ValueError, match="lead_time_days"):
        reorder_point.calculate_reorder_points(object())
