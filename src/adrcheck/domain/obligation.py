"""What an ADR actually binds. Compiled once per ADR; the judge checks these, not the prose."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Checkability(Enum):
    MECHANICAL = "mechanical"  # an import, a dependency, a path pattern: visible in the diff
    STRUCTURAL = "structural"  # dependency direction, ownership, boundary: needs module context
    INTENT = "intent"  # behavioural or semantic: defaults to UNCLEAR unless explicit
    PROCESS = "process"  # team practice: listed as not checkable, never flagged


@dataclass(frozen=True)
class Obligation:
    id: str
    adr_number: int
    kind: Literal["MUST", "MUST_NOT"]
    text: str
    quote: str
    checkability: Checkability
    mandates: tuple[str, ...] = ()  # identifiers or paths that should exist while the ADR holds
    forbids: tuple[str, ...] = ()  # patterns whose presence contradicts the ADR
