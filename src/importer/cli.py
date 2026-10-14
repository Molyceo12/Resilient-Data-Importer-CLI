"""Command-line interface for the importer.

Usage:
    python -m importer data/sample_users.csv --db output/users.json
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from importer.exceptions import ImporterError
from importer.logging_config import VALID_LEVELS, configure_logging
from importer.models import ImportSummary
from importer.parser import CsvParser
from importer.repository import JsonUserRepository
from importer.service import ImportService
from importer.validator import UserValidator

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "output/users.json"

EXIT_OK = 0
EXIT_FATAL = 1
EXIT_PARTIAL = 2


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser.

    Returns:
        A configured ``ArgumentParser``.
    """
    arg_parser = argparse.ArgumentParser(
        prog="importer",
        description="Import users from a CSV file into a JSON database.",
        epilog="Exit codes: 0 = all imported, 1 = fatal error, "
        "2 = finished with skipped rows.",
    )
    arg_parser.add_argument("csv_file", help="path to the CSV file to import")
    arg_parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"path to the JSON database (default: {DEFAULT_DB_PATH})",
    )
    arg_parser.add_argument(
        "--log-level",
        default="INFO",
        type=str.upper,
        choices=VALID_LEVELS,
        help="logging detail (default: INFO)",
    )
    return arg_parser


def format_summary(summary: ImportSummary) -> str:
    """Build the human-readable summary printed after an import.

    Args:
        summary: Result of the import run.

    Returns:
        Multi-line summary text.
    """
    lines = [
        "Import summary",
        "--------------",
        f"Imported:   {summary.imported}",
        f"Skipped:    {summary.skipped}",
        f"Duplicates: {summary.duplicates}",
    ]
    if summary.errors:
        lines.append("Problems:")
        lines.extend(f"  - {message}" for message in summary.errors)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the importer from the command line.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv[1:]`` when ``None``.

    Returns:
        Exit code: 0 if every row was imported, 1 on a fatal error, 2 if the
        import finished but some rows were skipped or duplicated.
    """
    args = build_arg_parser().parse_args(argv)
    configure_logging(args.log_level)

    service = ImportService(
        parser=CsvParser(),
        validator=UserValidator(),
        repository=JsonUserRepository(args.db),
    )

    try:
        summary = service.run(args.csv_file)
    except ImporterError as exc:
        logger.error("Import failed: %s", exc)
        print(f"Error: {exc}")
        return EXIT_FATAL

    print(format_summary(summary))
    return EXIT_PARTIAL if summary.has_problems else EXIT_OK
