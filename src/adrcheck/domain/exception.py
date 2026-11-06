"""`Adr-Exception: ADR-NNNN <reason>` trailers in a commit message waive one ADR for one change."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TRAILER = re.compile(r"^adr-exception:\s*(?:ADR[- ]?)?0*(\d+)[ \t]*(.*)$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class AdrException:
    adr_number: int
    reason: str


def parse_exceptions(message: str) -> tuple[tuple[AdrException, ...], tuple[str, ...]]:
    waived: list[AdrException] = []
    problems: list[str] = []
    for m in _TRAILER.finditer(message):
        number, reason = int(m.group(1)), m.group(2).strip()
        if reason:
            waived.append(AdrException(number, reason))
        else:
            problems.append(f"Adr-Exception for ADR-{number} has no reason and is ignored")
    return tuple(waived), tuple(problems)
