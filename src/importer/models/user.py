"""User data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class User:
    """A user record imported from CSV and stored in the JSON database.

    Attributes:
        user_id: Unique identifier of the user.
        name: Full name of the user.
        email: Email address of the user (stored lowercase).
    """

    user_id: str
    name: str
    email: str

    def to_dict(self) -> dict[str, str]:
        """Convert the user to a dictionary for JSON storage.

        Returns:
            A dictionary with ``user_id``, ``name`` and ``email`` keys.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> User:
        """Create a user from a dictionary loaded from JSON.

        Args:
            data: Dictionary with ``user_id``, ``name`` and ``email`` keys.

        Returns:
            The matching ``User`` instance.

        Raises:
            KeyError: If a required key is missing.
        """
        return cls(user_id=data["user_id"], name=data["name"], email=data["email"])
