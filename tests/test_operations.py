from datetime import date
from unittest.mock import Mock

import operations


def test_purge_audit_history_defaults_to_dry_run():
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = (3,)

    counts = operations.purge_audit_history(conn, date(2024, 1, 1))

    assert counts == {
        "pick_line_status_history": 3,
        "stock_adjustment_history": 3,
    }
    conn.commit.assert_not_called()


def test_report_failure_logs_stable_alert_marker(caplog):
    logger = Mock()
    operations.log_report_failure(logger, "reorder_points", RuntimeError())

    logger.error.assert_called_once_with(
        "alert=report_failure report=%s error_type=%s",
        "reorder_points",
        "RuntimeError",
    )
