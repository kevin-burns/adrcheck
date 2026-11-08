"""Scope an ADR from outside its text.

`Applies to` in the ADR header is the first home for scope. Teams whose ADRs are exports, archives
or someone else's wiki cannot edit the header, so a repo-side map supplies the same globs by ADR
number. The header wins when both exist, and the disagreement is reported rather than resolved:
two sources of one fact is a defect in the ADR set, not a merge to perform quietly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from adrcheck.domain.adr import Adr
from adrcheck.domain.lint import HygieneIssue

ScopeMap = Mapping[int, tuple[str, ...]]


def scope(adrs: list[Adr], mapping: ScopeMap) -> tuple[list[Adr], tuple[HygieneIssue, ...]]:
    issues: list[HygieneIssue] = []
    out: list[Adr] = []
    known: set[int] = set()
    for adr in adrs:
        paths = mapping.get(adr.number) if adr.number is not None else None
        if adr.number is not None:
            known.add(adr.number)
        if paths and not adr.applies_to:
            adr = replace(adr, applies_to=tuple(paths))
        elif paths and tuple(paths) != tuple(adr.applies_to):
            detail = f"header {', '.join(adr.applies_to)} wins over map {', '.join(paths)}"
            issues.append(HygieneIssue("scope-disagreement", adr.number, detail))
        out.append(adr)
    for number in sorted(set(mapping) - known):
        issues.append(HygieneIssue("map-unknown-adr", number, f"map names ADR-{number}, which does not exist"))
    return out, tuple(issues)
