"""Which accepted ADRs apply to a change, and why. Cheap signals only; the model is the caller's fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch

from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change

_ADR_REF = re.compile(r"\bADR[- ]?0*(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Selection:
    adr: Adr
    signals: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Exclusion:
    adr: Adr
    reason: str


@dataclass(frozen=True)
class SelectionResult:
    selected: tuple[Selection, ...] = ()
    excluded: tuple[Exclusion, ...] = ()
    undetermined: tuple[Selection, ...] = field(default=())


def _glob_matches(pattern: str, path: str) -> bool:
    if fnmatch(path, pattern):
        return True
    # `dir/**` should also match files directly under dir, as gitignore users expect.
    if pattern.endswith("/**") and path.startswith(pattern[:-2]):
        return True
    return False


def _referenced_numbers(change: Change) -> set[int]:
    texts = [change.message] + [line.text for f in change.files for line in f.lines()]
    return {int(n) for t in texts for n in _ADR_REF.findall(t)}


def select(adrs: list[Adr], change: Change) -> SelectionResult:
    refs = _referenced_numbers(change)
    selected: list[Selection] = []
    excluded: list[Exclusion] = []
    undetermined: list[Selection] = []
    for adr in adrs:
        if adr.status is not Status.ACCEPTED:
            excluded.append(Exclusion(adr, f"status is {adr.status.value}"))
            continue
        signals: set[str] = set()
        if adr.number is not None and adr.number in refs:
            signals.add("ref")
        if adr.applies_to and any(_glob_matches(p, path) for p in adr.applies_to for path in change.paths()):
            signals.add("glob")
        if signals:
            selected.append(Selection(adr, frozenset(signals)))
        elif adr.applies_to:
            excluded.append(Exclusion(adr, "globs did not match any changed path"))
        else:
            undetermined.append(Selection(adr))
    return SelectionResult(tuple(selected), tuple(excluded), tuple(undetermined))
