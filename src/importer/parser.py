"""CSV reading for the importer.

The parser only reads the file and hands back raw rows. It does not judge
whether a row is valid; that is the validator's job.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from importer.exceptions import CsvFileNotFoundError, FileFormatError

logger = logging.getLogger(__name__)

REQUIRED_HEADERS: tuple[str, ...] = ("user_id", "name", "email")


@dataclass(frozen=True)
class RawRow:
    """One unvalidated data row read from the CSV file.

    Attributes:
        line_number: Line in the file where the row starts.
        data: Values keyed by header name (missing values are ``""``).
        column_count: Number of values actually found in the row.
        expected_columns: Number of columns declared in the header.
    """

    line_number: int
    data: dict[str, str]
    column_count: int
    expected_columns: int


@contextmanager
def open_csv(path: Path) -> Iterator[TextIO]:
    """Open a CSV file for reading and always close it afterwards.

    Args:
        path: Path to the CSV file.

    Yields:
        The open text file handle.

    Raises:
        CsvFileNotFoundError: If the file does not exist.
        FileFormatError: If the file exists but cannot be opened.
    """
    try:
        handle = path.open(newline="", encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise CsvFileNotFoundError(str(path)) from exc
    except OSError as exc:
        raise FileFormatError(f"Cannot open CSV file {path}: {exc}") from exc

    try:
        yield handle
    finally:
        handle.close()
        logger.debug("Closed CSV file %s", path)


class CsvParser:
    """Reads user rows from a CSV file."""

    def __init__(self, required_headers: Sequence[str] = REQUIRED_HEADERS) -> None:
        """Initialise the parser.

        Args:
            required_headers: Column names that must appear in the header row.
        """
        self.required_headers: tuple[str, ...] = tuple(required_headers)

    def parse(self, path: str | Path) -> Iterator[RawRow]:
        """Yield the data rows of a CSV file one at a time.

        Blank lines are skipped. Header names are matched case-insensitively
        and surrounding spaces are ignored.

        Args:
            path: Path to the CSV file.

        Yields:
            A ``RawRow`` for every non-blank data line.

        Raises:
            CsvFileNotFoundError: If the file does not exist.
            FileFormatError: If the file is empty, has missing headers or
                cannot be decoded as CSV text.
        """
        csv_path = Path(path)
        row_count = 0
        logger.info("Reading CSV file %s", csv_path)

        with open_csv(csv_path) as handle:
            reader = csv.reader(handle)
            try:
                headers = self._read_headers(reader, csv_path)
                for values in reader:
                    if not any(value.strip() for value in values):
                        continue
                    row_count += 1
                    yield self._build_row(reader.line_num, headers, values)
            except (csv.Error, UnicodeDecodeError) as exc:
                raise FileFormatError(
                    f"Cannot read CSV file {csv_path} near line {reader.line_num}: "
                    f"{exc}"
                ) from exc
            else:
                logger.info("Read %d data rows from %s", row_count, csv_path)
            finally:
                logger.debug("Stopped reading %s after %d rows", csv_path, row_count)

    def _read_headers(self, reader: Iterator[list[str]], path: Path) -> list[str]:
        """Read and check the header row.

        Args:
            reader: CSV reader positioned at the start of the file.
            path: Path of the file, used in error messages.

        Returns:
            Normalised (lowercase, stripped) header names.

        Raises:
            FileFormatError: If the file is empty or required headers are missing.
        """
        header_row = next(reader, None)
        if header_row is None:
            raise FileFormatError(f"CSV file is empty: {path}")

        headers = [name.strip().lower() for name in header_row]
        missing = [name for name in self.required_headers if name not in headers]
        if missing:
            raise FileFormatError(
                f"CSV file {path} is missing required headers: {', '.join(missing)}"
            )
        return headers

    @staticmethod
    def _build_row(line_number: int, headers: list[str], values: list[str]) -> RawRow:
        """Pair header names with row values.

        Args:
            line_number: Line where the row starts.
            headers: Normalised header names.
            values: Raw values from the CSV reader.

        Returns:
            The row as a ``RawRow``; missing values become ``""``.
        """
        data = {
            header: values[index].strip() if index < len(values) else ""
            for index, header in enumerate(headers)
        }
        return RawRow(
            line_number=line_number,
            data=data,
            column_count=len(values),
            expected_columns=len(headers),
        )
