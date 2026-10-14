"""Import result models."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RowProblem:
    """A CSV row that was not imported.

    Attributes:
        line_number: Line in the CSV file where the row starts.
        kind: Short category, ``"invalid"`` or ``"duplicate"``.
        details: Human-readable explanation of the problem.
    """

    line_number: int
    kind: str
    details: str


@dataclass
class ImportSummary:
    """Counts and problems collected during one import run.

    Attributes:
        imported: Number of users added to the database.
        skipped: Number of rows rejected by validation.
        duplicates: Number of rows whose user id or email already existed.
        problems: One entry per skipped or duplicate row.
    """

    imported: int = 0
    skipped: int = 0
    duplicates: int = 0
    problems: list[RowProblem] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        """Return the number of data rows processed.

        Returns:
            Sum of imported, skipped and duplicate rows.
        """
        return self.imported + self.skipped + self.duplicates

    @property
    def has_problems(self) -> bool:
        """Return whether any row was skipped or duplicated.

        Returns:
            ``True`` if at least one row was not imported.
        """
        return self.skipped > 0 or self.duplicates > 0
