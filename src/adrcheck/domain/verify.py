"""The judge's claim is checked against exactly what it was shown, before anyone sees it.

Three rules, one function. A claim survives only if the line is one the change added or
removed, the quote appears verbatim in the ADR, and the quote comes from the part of the ADR
that binds (Decision or Consequences), never from Context or Considered Options, which describe
the problem and the roads not taken.
"""

from __future__ import annotations

from dataclasses import dataclass

from adrcheck.domain.adr import Adr
from adrcheck.domain.change import Change

BINDING_SECTIONS = ("decision", "consequences")


@dataclass(frozen=True)
class Claim:
    adr_number: int
    path: str
    line_text: str
    quote: str


@dataclass(frozen=True)
class VerifyResult:
    failed: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.failed


def _normalise(text: str) -> str:
    return " ".join(text.split())


def verify(claim: Claim, change: Change, adr: Adr) -> VerifyResult:
    failed: list[str] = []
    if not change.touched(claim.path, claim.line_text):
        failed.append("line-not-in-change")
    quote = _normalise(claim.quote)
    everywhere = _normalise(" ".join(adr.sections.values()))
    binding = _normalise(" ".join(adr.section(s) for s in BINDING_SECTIONS))
    if quote not in everywhere:
        failed.append("quote-not-in-adr")
    elif quote not in binding:
        failed.append("quote-outside-decision")
    return VerifyResult(failed=tuple(failed))
