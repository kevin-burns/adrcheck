"""Hygiene of the ADR set itself. Deterministic; a status mismatch is also evidence an ADR is overtaken."""

from __future__ import annotations

from dataclasses import dataclass

from adrcheck.domain.adr import Adr, Status


@dataclass(frozen=True)
class HygieneIssue:
    kind: str
    adr_number: int | None
    detail: str


def _cycle_from(start: int, succ: dict[int, tuple[int, ...]]) -> tuple[int, ...] | None:
    path, seen = [start], {start}
    node = start
    while True:
        nxt = next((n for n in succ.get(node, ()) if n in succ), None)
        if nxt is None:
            return None
        path.append(nxt)
        if nxt == start:
            return tuple(path)
        if nxt in seen:
            return None
        seen.add(nxt)
        node = nxt


def lint(adrs: list[Adr]) -> tuple[HygieneIssue, ...]:
    by_number = {a.number: a for a in adrs if a.number is not None}
    issues: list[HygieneIssue] = []
    supersedes = {a.number: a.supersedes for a in adrs if a.number is not None and a.supersedes}
    reported_cycles: set[frozenset[int]] = set()

    seen_numbers: dict[int, Adr] = {}
    for adr in adrs:
        if adr.number is not None:
            if (first := seen_numbers.get(adr.number)) is not None:
                detail = f"two records share number {adr.number}: {first.source} and {adr.source}"
                issues.append(HygieneIssue("duplicate-number", adr.number, detail))
            else:
                seen_numbers[adr.number] = adr
        if adr.status is Status.UNKNOWN:
            issues.append(HygieneIssue("missing-status", adr.number, "no recognisable Status"))
        if adr.status is Status.ACCEPTED and not (adr.section("decision") or adr.section("consequences")).strip():
            issues.append(
                HygieneIssue(
                    "no-binding-section", adr.number, "no decision or consequences section found; nothing binds"
                )
            )
        if adr.number is not None and adr.number in (*adr.supersedes, *adr.superseded_by):
            issues.append(HygieneIssue("self-supersede", adr.number, f"ADR-{adr.number} supersedes itself"))
        if len(targets := sorted(set(adr.superseded_by))) > 1:
            names = " and ".join(f"ADR-{n}" for n in targets)
            detail = f"superseded by {names}; one decision has one successor"
            issues.append(HygieneIssue("multiple-supersede-targets", adr.number, detail))
        for old in adr.supersedes:
            if old == adr.number:
                continue
            if old not in by_number:
                issues.append(
                    HygieneIssue("dangling-supersede-ref", adr.number, f"supersedes ADR-{old}, which does not exist")
                )
            elif by_number[old].status is not Status.SUPERSEDED and adr.status is not Status.PROPOSED:
                # a proposed successor is a pending proposal; the old decision holds until the new one is accepted
                issues.append(
                    HygieneIssue(
                        "status-mismatch",
                        old,
                        f"superseded by ADR-{adr.number} but status is {by_number[old].status.value}",
                    )
                )
        if adr.number is not None and (cycle := _cycle_from(adr.number, supersedes)):
            key = frozenset(cycle)
            if key not in reported_cycles:
                reported_cycles.add(key)
                issues.append(HygieneIssue("supersede-cycle", adr.number, " -> ".join(f"ADR-{n}" for n in cycle)))
    return tuple(issues)
