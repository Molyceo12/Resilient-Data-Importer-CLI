"""User storage using the repository pattern.

``UserRepository`` defines what storage must do; ``JsonUserRepository`` is the
JSON-file implementation. Other code depends only on the abstract interface,
so the storage can be swapped (or mocked in tests) without changing it.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from importer.exceptions import DuplicateUserError, StorageError
from importer.models import User

logger = logging.getLogger(__name__)


class UserRepository(ABC):
    """Interface for storing users."""

    @abstractmethod
    def get_all(self) -> list[User]:
        """Return every stored user.

        Returns:
            All users, in insertion order.
        """

    @abstractmethod
    def add(self, user: User) -> None:
        """Add a new user.

        Args:
            user: The user to add.

        Raises:
            DuplicateUserError: If the user id or email is already stored.
        """

    @abstractmethod
    def save(self) -> None:
        """Persist all added users.

        Raises:
            StorageError: If the data cannot be written.
        """


@contextmanager
def atomic_write(path: Path) -> Iterator[TextIO]:
    """Write a file so that it is either fully replaced or left untouched.

    Data goes to a temporary file in the same folder, which replaces the
    target only after writing succeeds. A crash mid-write never leaves a
    half-written database behind.

    Args:
        path: Final location of the file.

    Yields:
        A text handle to write the new content to.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yield handle
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    else:
        os.replace(tmp_path, path)


class JsonUserRepository(UserRepository):
    """Stores users in a JSON file containing a list of user objects.

    Users are loaded once on first use and kept in memory; ``save`` writes
    them all back in one go.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialise the repository.

        Args:
            path: Location of the JSON database file. It is created on the
                first save if it does not exist.
        """
        self.path = Path(path)
        self._users: dict[str, User] | None = None
        self._emails: set[str] = set()

    def get_all(self) -> list[User]:
        """Return every stored user, including unsaved ones.

        Returns:
            All users, in insertion order.

        Raises:
            StorageError: If the existing database cannot be read.
        """
        return list(self._load().values())

    def add(self, user: User) -> None:
        """Add a user in memory; call ``save`` to persist.

        Args:
            user: The user to add.

        Raises:
            DuplicateUserError: If the user id or email is already stored.
            StorageError: If the existing database cannot be read.
        """
        users = self._load()
        if user.user_id in users:
            raise DuplicateUserError(user.user_id, "user_id")
        if user.email.lower() in self._emails:
            raise DuplicateUserError(user.user_id, "email")

        users[user.user_id] = user
        self._emails.add(user.email.lower())
        logger.debug("Added user %s to repository", user.user_id)

    def save(self) -> None:
        """Write all users to the JSON file atomically.

        Raises:
            StorageError: If the file cannot be written.
        """
        records = [user.to_dict() for user in self._load().values()]
        try:
            with atomic_write(self.path) as handle:
                json.dump(records, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        except OSError as exc:
            raise StorageError(f"Cannot write database {self.path}: {exc}") from exc
        logger.info("Saved %d users to %s", len(records), self.path)

    def _load(self) -> dict[str, User]:
        """Load users from disk the first time they are needed.

        Returns:
            Users keyed by user id.

        Raises:
            StorageError: If the file cannot be read or has invalid content.
        """
        if self._users is not None:
            return self._users

        users: dict[str, User] = {}
        if self.path.exists():
            for record in self._read_records():
                user = User.from_dict(record)
                users[user.user_id] = user
                self._emails.add(user.email.lower())
            logger.info("Loaded %d existing users from %s", len(users), self.path)
        else:
            logger.info("Database %s not found; starting empty", self.path)

        self._users = users
        return users

    def _read_records(self) -> list[dict[str, str]]:
        """Read and check the raw records in the JSON file.

        Returns:
            A list of user dictionaries.

        Raises:
            StorageError: If the file is unreadable, not valid JSON or not a
                list of user objects.
        """
        try:
            with self.path.open(encoding="utf-8") as handle:
                data: object = json.load(handle)
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"Database {self.path} is not valid JSON: {exc}"
            ) from exc
        except OSError as exc:
            raise StorageError(f"Cannot read database {self.path}: {exc}") from exc

        if not isinstance(data, list):
            raise StorageError(f"Database {self.path} must contain a JSON list")

        records: list[dict[str, str]] = []
        for index, item in enumerate(data):
            if not (
                isinstance(item, dict)
                and all(
                    isinstance(item.get(key), str)
                    for key in ("user_id", "name", "email")
                )
            ):
                raise StorageError(
                    f"Database {self.path} has an invalid record at index {index}"
                )
            records.append({key: item[key] for key in ("user_id", "name", "email")})
        return records
