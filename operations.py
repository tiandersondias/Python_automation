import logging
from datetime import date

import psycopg


def purge_audit_history(
    conn: psycopg.Connection, before: date, *, dry_run: bool = True
) -> dict[str, int]:
    """Count or delete audit rows older than ``before``."""
    counts = {}
    for table in ("pick_line_status_history", "stock_adjustment_history"):
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE changed_at < %s",
            (before,),
        ).fetchone()[0]
        counts[table] = count
        if not dry_run and count:
            conn.execute(
                f"DELETE FROM {table} WHERE changed_at < %s",
                (before,),
            )

    if not dry_run:
        conn.commit()
    return counts


def log_report_failure(logger: logging.Logger, report: str, error: Exception) -> None:
    """Emit a stable alert marker for external log-based monitoring."""
    logger.error(
        "alert=report_failure report=%s error_type=%s", report, type(error).__name__
    )
