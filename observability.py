import logging
import sys
from datetime import UTC, datetime


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    return logging.getLogger("warehouse")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
