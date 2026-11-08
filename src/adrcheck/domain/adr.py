"""An architecture decision record, independent of the markdown format it came from."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class Status(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    UNKNOWN = "unknown"

    @classmethod
    def parse(cls, text: str) -> Status:
        head = text.strip().lower()
        for status in cls:
            if head.startswith(status.value):
                return status
        for alias, status in _STATUS_ALIASES.items():
            if head.startswith(alias):
                return status
        return cls.UNKNOWN


# Status words other templates and wikis use. Unknown stays UNKNOWN: lint reports it, nothing assumes accepted.
_STATUS_ALIASES: dict[str, Status] = {
    "decided": Status.ACCEPTED,
    "approved": Status.ACCEPTED,
    "adopted": Status.ACCEPTED,
    "done": Status.ACCEPTED,
    "draft": Status.PROPOSED,
    "in progress": Status.PROPOSED,
    "in review": Status.PROPOSED,
    "not started": Status.PROPOSED,
    "pending": Status.PROPOSED,
    "retired": Status.DEPRECATED,
    "obsolete": Status.DEPRECATED,
    "replaced": Status.SUPERSEDED,
    "declined": Status.REJECTED,
    "withdrawn": Status.REJECTED,
}


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

    def missing_roles(
        self, roles: tuple[str, ...] = ("decision", "consequences", "context", "options")
    ) -> tuple[str, ...]:
        """Roles this record does not carry. Reported, never guessed: a shape without an options role has none."""
        return tuple(r for r in roles if not self.sections.get(r, "").strip())
