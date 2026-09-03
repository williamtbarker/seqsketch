"""Validated public data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SequenceRecord:
    """A named symbolic sequence with an optional ordered period."""

    identifier: str
    sequence: str
    period: int | None = None

    def __post_init__(self) -> None:
        if not self.identifier or any(character.isspace() for character in self.identifier):
            raise ValueError("identifier must be non-empty and contain no whitespace")
        if not self.sequence or not self.sequence.isascii() or not self.sequence.isalpha():
            raise ValueError("sequence must be non-empty ASCII alphabetic text")
        if self.period is not None:
            if not isinstance(self.period, int) or isinstance(self.period, bool):
                raise TypeError("period must be an integer or null")
            if self.period < 0:
                raise ValueError("period must be non-negative")


@dataclass(frozen=True, slots=True)
class Neighbor:
    """One similarity-search result."""

    identifier: str
    jaccard: float
    estimated_jaccard: float


@dataclass(frozen=True, slots=True)
class TemporalEdge:
    """A similarity edge directed from an older record to a newer record."""

    source: str
    target: str
    jaccard: float
    estimated_jaccard: float
    period_delta: int
