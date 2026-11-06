"""An architecture decision record, independent of the markdown format it came from."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class Status(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    UNKNOWN = "unknown"

    @classmethod
    def parse(cls, text: str) -> "Status":
        head = text.strip().lower()
        for status in cls:
            if head.startswith(status.value):
                return status
        return cls.UNKNOWN


@dataclass(frozen=True)
class Adr:
    """One decision. `sections` is keyed by canonical name: context, decision, consequences."""

    title: str
    status: Status
    source: str
    number: int | None = None
    date: str | None = None
    applies_to: tuple[str, ...] = ()
    sections: Mapping[str, str] = field(default_factory=dict)
    supersedes: tuple[int, ...] = ()
    superseded_by: tuple[int, ...] = ()

    def section(self, name: str) -> str:
        return self.sections.get(name, "")
