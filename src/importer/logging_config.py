"""Logging setup for the importer.

Modules create their own logger with ``logging.getLogger(__name__)``; this
module only configures where and how those messages are written. It is called
once from the CLI, never at import time.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    console: bool = True,
) -> None:
    """Configure the root logger to write structured log lines.

    Args:
        level: Minimum level to record, e.g. ``"INFO"`` or ``"DEBUG"``
            (case-insensitive).
        log_file: Optional file to append log lines to. Its folder is
            created if needed.
        console: Whether to also write log lines to stderr. If the log file
            cannot be opened, stderr is used regardless.

    Raises:
        ValueError: If ``level`` is not a valid logging level name.
    """
    level_name = level.upper()
    if level_name not in VALID_LEVELS:
        raise ValueError(f"Invalid log level: {level}")

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handlers: list[logging.Handler] = []
    file_error: OSError | None = None

    if log_file is not None:
        path = Path(log_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(path, encoding="utf-8"))
        except OSError as exc:
            file_error = exc

    if console or not handlers:
        handlers.append(logging.StreamHandler(sys.stderr))

    root = logging.getLogger()
    for old in root.handlers[:]:
        root.removeHandler(old)
        old.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level_name)

    if file_error is not None:
        logging.getLogger(__name__).warning(
            "Cannot write log file %s (%s); logging to console", log_file, file_error
        )
