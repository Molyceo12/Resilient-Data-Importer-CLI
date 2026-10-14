"""Logging setup for the importer.

Modules create their own logger with ``logging.getLogger(__name__)``; this
module only configures where and how those messages are written. It is called
once from the CLI, never at import time.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to write structured lines to stderr.

    Args:
        level: Minimum level to show, e.g. ``"INFO"`` or ``"DEBUG"``
            (case-insensitive).

    Raises:
        ValueError: If ``level`` is not a valid logging level name.
    """
    level_name = level.upper()
    if level_name not in VALID_LEVELS:
        raise ValueError(f"Invalid log level: {level}")

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level_name)
