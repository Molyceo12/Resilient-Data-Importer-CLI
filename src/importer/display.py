"""Terminal output for the importer.

Builds the boxed report shown after an import and the message shown when an
import fails. Every line is framed with ``::`` on both sides; long values are
wrapped so the right border always lines up. Only plain ASCII is used so the
output works in any terminal, including the Windows console.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from importer.exceptions import (
    CsvFileNotFoundError,
    FileFormatError,
    ImporterError,
    StorageError,
)
from importer.models import ImportSummary, RowProblem

WIDTH = 72
BORDER = "::"
SEPARATOR = ":" * WIDTH
INNER = WIDTH - 2 * len(BORDER)  # space between the side borders
CONTENT = INNER - 1  # keep one blank column before the right border
TITLE = "RESILIENT DATA IMPORTER"

LABEL_COL = 14
VALUE_INDENT = 2 + LABEL_COL + 3  # "  " + label + " : "
LINE_COL = 6
TYPE_COL = 11
DETAILS_COL = CONTENT - 2 - LINE_COL - TYPE_COL - 2

TIPS: dict[type[ImporterError], str] = {
    CsvFileNotFoundError: "Check the CSV file path and try again.",
    FileFormatError: "Use a UTF-8 CSV file whose first row is: user_id,name,email",
    StorageError: "Check the --db path, or fix or remove the broken database file.",
}


def _wrap(text: str, width: int) -> list[str]:
    """Split text into lines no wider than ``width``.

    Long words without spaces (such as file paths) are split too.

    Args:
        text: Text to wrap.
        width: Maximum line width.

    Returns:
        The wrapped lines (at least one, possibly empty).
    """
    return textwrap.wrap(text, width, break_on_hyphens=False) or [""]


def _field(label: str, value: object) -> list[str]:
    """Format a ``label : value`` pair, wrapping long values under the value.

    Args:
        label: Text on the left.
        value: Value on the right.

    Returns:
        One or more aligned lines.
    """
    parts = _wrap(str(value), CONTENT - VALUE_INDENT)
    lines = [f"  {label:<{LABEL_COL}} : {parts[0]}"]
    lines.extend(" " * VALUE_INDENT + part for part in parts[1:])
    return lines


def _problem_rows(problems: list[RowProblem]) -> list[str]:
    """Format problems as table rows, wrapping long details.

    Args:
        problems: Rows that were not imported.

    Returns:
        Table lines, including the header.
    """
    lines = [
        f"  {'LINE':<{LINE_COL}}{'TYPE':<{TYPE_COL}}  DETAILS",
        f"  {'-' * (LINE_COL - 2):<{LINE_COL}}{'-' * (TYPE_COL - 2):<{TYPE_COL}}  "
        + "-" * DETAILS_COL,
    ]
    indent = " " * (2 + LINE_COL + TYPE_COL + 2)
    for problem in problems:
        wrapped = _wrap(problem.details, DETAILS_COL)
        line = f"{problem.line_number:<{LINE_COL}}"
        kind = f"{problem.kind:<{TYPE_COL}}"
        lines.append(f"  {line}{kind}  {wrapped[0]}")
        lines.extend(indent + part for part in wrapped[1:])
    return lines


def _status(summary: ImportSummary) -> list[str]:
    """Return the verdict for an import.

    Args:
        summary: Result of the import run.

    Returns:
        The status message, wrapped to fit the box.
    """
    not_imported = summary.skipped + summary.duplicates
    if summary.total_rows == 0:
        message = "[i]  No data rows found in the file. Nothing was imported."
    elif not_imported == 0:
        message = f"[OK] All {summary.imported} row(s) imported successfully."
    elif summary.imported == 0:
        message = f"[!]  No rows imported. {not_imported} row(s) had problems."
    else:
        message = (
            f"[!]  Import finished: {summary.imported} imported, "
            f"{not_imported} row(s) need attention."
        )
    # Continuation lines line up with the text after the "[!]  " marker.
    parts = textwrap.wrap(message, CONTENT - 2, subsequent_indent=" " * 5)
    return ["  " + part for part in parts]


def _box(*sections: list[str]) -> str:
    """Frame sections of text in a ``::`` box under the title banner.

    Args:
        *sections: Groups of content lines; a separator is drawn after each.

    Returns:
        The complete framed text.
    """
    lines = [SEPARATOR, f"{BORDER}{TITLE.center(INNER)}{BORDER}", SEPARATOR]
    for section in sections:
        lines.extend(f"{BORDER}{text:<{INNER}}{BORDER}" for text in section)
        lines.append(SEPARATOR)
    return "\n".join(lines)


def render_report(
    summary: ImportSummary,
    csv_path: str | Path,
    db_path: str | Path,
    log_file: str | Path | None,
    elapsed_seconds: float,
) -> str:
    """Build the report shown after an import finishes.

    Args:
        summary: Result of the import run.
        csv_path: CSV file that was imported.
        db_path: JSON database that was updated.
        log_file: Where detailed logs were written, if anywhere.
        elapsed_seconds: How long the import took.

    Returns:
        The full framed report.
    """
    files = [*_field("Source file", csv_path), *_field("Database", db_path)]
    if log_file is not None:
        files += _field("Log file", log_file)

    results = [
        "  IMPORT RESULTS",
        "",
        *_field("[+] Imported", f"{summary.imported:>5}"),
        *_field("[-] Skipped", f"{summary.skipped:>5}"),
        *_field("[=] Duplicate", f"{summary.duplicates:>5}"),
        "  " + "-" * 22,
        *_field("    Total", f"{summary.total_rows:>5}"),
    ]

    status = [*_status(summary), f"  Finished in {elapsed_seconds:.2f}s"]

    if summary.problems:
        problems = [
            f"  PROBLEMS ({len(summary.problems)})",
            "",
            *_problem_rows(summary.problems),
        ]
        return _box(files, results, problems, status)
    return _box(files, results, status)


def render_error(error: ImporterError, csv_path: str | Path) -> str:
    """Build the message shown when an import stops with a fatal error.

    Args:
        error: The error that stopped the import.
        csv_path: CSV file that was being imported.

    Returns:
        The full framed error message.
    """
    tip = next(
        (text for kind, text in TIPS.items() if isinstance(error, kind)),
        "See the log file for details.",
    )
    headline = ["  [X]  IMPORT FAILED - nothing was saved"]
    details = [
        *_field("Source file", csv_path),
        *_field("Reason", error),
        *_field("Tip", tip),
    ]
    return _box(headline, details)
