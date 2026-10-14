"""Custom exception hierarchy for the importer.

Every error the tool raises on purpose inherits from ``ImporterError``, so
callers can catch all expected failures with a single ``except`` clause while
still handling specific cases when needed.
"""


class ImporterError(Exception):
    """Base class for all importer errors."""


class CsvFileNotFoundError(ImporterError):
    """Raised when the CSV file to import does not exist."""

    def __init__(self, path: str) -> None:
        """Initialise the error.

        Args:
            path: Path of the missing CSV file.
        """
        self.path = path
        super().__init__(f"CSV file not found: {path}")


class FileFormatError(ImporterError):
    """Raised when the CSV file is empty, unreadable or has wrong headers."""


class ValidationError(ImporterError):
    """Raised when a single CSV row contains invalid data."""

    def __init__(self, line_number: int, field: str, reason: str) -> None:
        """Initialise the error.

        Args:
            line_number: Line in the CSV file where the problem was found.
            field: Name of the invalid field.
            reason: Human-readable explanation of the problem.
        """
        self.line_number = line_number
        self.field = field
        self.reason = reason
        super().__init__(f"Line {line_number}: invalid '{field}' ({reason})")


class DuplicateUserError(ImporterError):
    """Raised when a user with the same id or email is already stored."""

    def __init__(self, user_id: str, field: str) -> None:
        """Initialise the error.

        Args:
            user_id: Id of the user that could not be added.
            field: Field that caused the clash (``user_id`` or ``email``).
        """
        self.user_id = user_id
        self.field = field
        super().__init__(f"Duplicate user '{user_id}': {field} already exists")


class StorageError(ImporterError):
    """Raised when the JSON database cannot be read or written."""
