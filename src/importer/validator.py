"""Row validation: turns raw CSV rows into ``User`` objects."""

from __future__ import annotations

import re

from importer.exceptions import ValidationError
from importer.models import User
from importer.parser import RawRow

# Simple, practical check: something@something.tld with no spaces.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_NAME_LENGTH = 100


class UserValidator:
    """Checks a raw CSV row and builds a ``User`` from it."""

    def validate(self, row: RawRow) -> User:
        """Validate one row and convert it to a user.

        Args:
            row: Raw row produced by the CSV parser.

        Returns:
            A ``User`` with trimmed values and a lowercase email.

        Raises:
            ValidationError: If the row has the wrong number of columns, a
                required field is empty, the name is too long or the email
                is not valid.
        """
        if row.column_count != row.expected_columns:
            raise ValidationError(
                row.line_number,
                "row",
                f"expected {row.expected_columns} columns, got {row.column_count}",
            )

        user_id = self._require(row, "user_id")
        name = self._require(row, "name")
        email = self._require(row, "email").lower()

        if len(name) > MAX_NAME_LENGTH:
            raise ValidationError(
                row.line_number, "name", f"longer than {MAX_NAME_LENGTH} characters"
            )
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValidationError(row.line_number, "email", f"'{email}' is not valid")

        return User(user_id=user_id, name=name, email=email)

    @staticmethod
    def _require(row: RawRow, field: str) -> str:
        """Return a field's value, failing if it is empty.

        Args:
            row: Raw row to read from.
            field: Name of the required field.

        Returns:
            The non-empty, stripped value.

        Raises:
            ValidationError: If the value is missing or blank.
        """
        value = row.data.get(field, "").strip()
        if not value:
            raise ValidationError(row.line_number, field, "value is empty")
        return value
