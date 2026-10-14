"""Terminal output for the importer.

Builds the boxed report shown after an import and the message shown when an
import fails. Only plain ASCII is used so the output works in any terminal,
including the Windows console and redirected output.
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

WIDTH = 64
SEPARATOR = ":" * WIDTH
TITLE = "RESILIENT DATA IMPORTER"

LABEL_COL = 14
VALUE_INDENT = 2 + LABEL_COL + 3
LINE_COL = 6
TYPE_COL = 11
DETAILS_COL = WIDTH - 2 - LINE_COL - TYPE_COL - 2

TIPS: dict[type[ImporterError], str] = {
    CsvFileNotFoundError: "Check the CSV file path and try again.",
    FileFormatError: ("Use a UTF-8 CSV file whose first row is: user_id,name,email"),
    StorageError: "Check the --db path, or fix or remove the broken database file.",
}


def _banner() -> list[str]:
    """Return the title block.

    Returns:
        Lines of the banner.
    """
    inner = WIDTH - 4
    return [SEPARATOR, f"::{TITLE.center(inner)}::", SEPARATOR]


def _field(label: str, value: object) -> str:
    """Format one ``label : value`` line.

    Args:
        label: Text on the left.
        value: Value on the right.

    Returns:
        The aligned line.
    """
    return f"  {label:<{LABEL_COL}} : {value}"


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
    for problem in problems:
        wrapped = textwrap.wrap(problem.details, DETAILS_COL) or [""]
        line = f"{problem.line_number:<{LINE_COL}}"
        kind = f"{problem.kind:<{TYPE_COL}}"
        lines.append(f"  {line}{kind}  {wrapped[0]}")
        indent = " " * (2 + LINE_COL + TYPE_COL + 2)
        lines.extend(f"{indent}{part}" for part in wrapped[1:])
    return lines


def _status(summary: ImportSummary) -> str:
    """Return the one-line verdict for an import.

    Args:
        summary: Result of the import run.

    Returns:
        A short status message.
    """
    not_imported = summary.skipped + summary.duplicates
    if summary.total_rows == 0:
        return "[i]  No data rows found in the file. Nothing was imported."
    if not_imported == 0:
        return f"[OK] All {summary.imported} row(s) imported successfully."
    if summary.imported == 0:
        return f"[!]  No rows imported. {not_imported} row(s) had problems."
    return (
        f"[!]  Import finished: {summary.imported} imported, "
        f"{not_imported} row(s) need attention."
    )


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
        The full multi-line report.
    """
    lines = _banner()
    lines += [
        _field("Source file", csv_path),
        _field("Database", db_path),
    ]
    if log_file is not None:
        lines.append(_field("Log file", log_file))
    lines += [
        SEPARATOR,
        "  IMPORT RESULTS",
        "",
        _field("[+] Imported", f"{summary.imported:>5}"),
        _field("[-] Skipped", f"{summary.skipped:>5}"),
        _field("[=] Duplicate", f"{summary.duplicates:>5}"),
        "  " + "-" * 22,
        _field("    Total", f"{summary.total_rows:>5}"),
    ]
    if summary.problems:
        lines += [
            SEPARATOR,
            f"  PROBLEMS ({len(summary.problems)})",
            "",
            *_problem_rows(summary.problems),
        ]
    lines += [
        SEPARATOR,
        f"  {_status(summary)}",
        f"  Finished in {elapsed_seconds:.2f}s",
        SEPARATOR,
    ]
    return "\n".join(lines)


def render_error(error: ImporterError, csv_path: str | Path) -> str:
    """Build the message shown when an import stops with a fatal error.

    Args:
        error: The error that stopped the import.
        csv_path: CSV file that was being imported.

    Returns:
        The full multi-line error message.
    """
    tip = next(
        (text for kind, text in TIPS.items() if isinstance(error, kind)),
        "See the log file for details.",
    )
    reason = textwrap.wrap(str(error), WIDTH - VALUE_INDENT) or [""]
    lines = _banner()
    lines += [
        "  [X]  IMPORT FAILED - nothing was saved",
        SEPARATOR,
        _field("Source file", csv_path),
        _field("Reason", reason[0]),
    ]
    lines.extend(f"{' ' * VALUE_INDENT}{part}" for part in reason[1:])
    lines += [
        _field("Tip", tip),
        SEPARATOR,
    ]
    return "\n".join(lines)
