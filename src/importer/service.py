"""Import service: runs parse → validate → store for one CSV file."""

from __future__ import annotations

import logging
from pathlib import Path

from importer.exceptions import DuplicateUserError, ValidationError
from importer.models import ImportSummary, RowProblem
from importer.parser import CsvParser
from importer.repository import UserRepository
from importer.validator import UserValidator

logger = logging.getLogger(__name__)


class ImportService:
    """Coordinates the parser, validator and repository.

    The parts are passed in rather than created here, so each one can be
    replaced (for example with a mock in tests) without changing this class.
    """

    def __init__(
        self,
        parser: CsvParser,
        validator: UserValidator,
        repository: UserRepository,
    ) -> None:
        """Initialise the service.

        Args:
            parser: Reads raw rows from the CSV file.
            validator: Turns raw rows into ``User`` objects.
            repository: Stores the users.
        """
        self.parser = parser
        self.validator = validator
        self.repository = repository

    def run(self, csv_path: str | Path) -> ImportSummary:
        """Import every valid user from a CSV file.

        Invalid and duplicate rows are skipped and recorded in the summary;
        the import carries on with the next row. Users are saved once, after
        all rows have been processed.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            Counts of imported, skipped and duplicate rows, with messages.

        Raises:
            CsvFileNotFoundError: If the CSV file does not exist.
            FileFormatError: If the CSV file is empty, unreadable or has
                missing headers.
            StorageError: If the database cannot be read or written.
        """
        summary = ImportSummary()
        logger.info("Starting import from %s", csv_path)

        try:
            for row in self.parser.parse(csv_path):
                try:
                    user = self.validator.validate(row)
                    self.repository.add(user)
                except ValidationError as exc:
                    summary.skipped += 1
                    summary.problems.append(
                        RowProblem(
                            exc.line_number, "invalid", f"{exc.field}: {exc.reason}"
                        )
                    )
                    logger.warning("Skipped row: %s", exc)
                except DuplicateUserError as exc:
                    summary.duplicates += 1
                    summary.problems.append(
                        RowProblem(
                            row.line_number,
                            "duplicate",
                            f"{exc.field} already exists (user {exc.user_id})",
                        )
                    )
                    logger.warning(
                        "Skipped duplicate at line %d: %s", row.line_number, exc
                    )
                else:
                    summary.imported += 1
                    logger.info("Imported user %s", user.user_id)

            self.repository.save()
        finally:
            logger.info(
                "Import finished: %d imported, %d skipped, %d duplicates",
                summary.imported,
                summary.skipped,
                summary.duplicates,
            )

        return summary
