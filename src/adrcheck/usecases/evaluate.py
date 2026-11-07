"""Score a check report against frozen cases. A case is a labelled (commit, ADR, binding quote) with the
verdict a careful reader gave it. Quotes identify obligations because obligation ids change on every
recompile and verbatim ADR text does not. No I/O: the caller loads both sides."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    commit: str
    adr: int
    quote: str
    expected: str
    note: str = ""


@dataclass(frozen=True)
class CaseResult:
    case: Case
    outcome: str  # hit | quiet (COMPLIANT expected, nothing raised) | miss | absent
    got: str | None


@dataclass(frozen=True)
class Score:
    rows: tuple[CaseResult, ...]
    matrix: Counter = field(default_factory=Counter)  # (expected, got) -> count; got is None when absent

    @property
    def hits(self) -> int:
        return sum(1 for r in self.rows if r.outcome in ("hit", "quiet"))

    @property
    def total(self) -> int:
        return len(self.rows)


def _norm(text: str) -> str:
    return " ".join(text.split())


def _same_obligation(case_quote: str, finding_quote: str) -> bool:
    a, b = _norm(case_quote), _norm(finding_quote)
    return bool(a) and bool(b) and (a in b or b in a)


def score(cases: tuple[Case, ...], findings: list[dict]) -> Score:
    rows: list[CaseResult] = []
    matrix: Counter = Counter()
    for case in cases:
        got: str | None = None
        for f in findings:
            if not str(f.get("commit", "")).startswith(case.commit) or int(f.get("adr", -1)) != case.adr:
                continue
            quote = str(f.get("quote") or "")
            if _same_obligation(case.quote, quote):
                got = str(f.get("verdict"))
                break
            # An ADR-level verdict with no quote covers every obligation of that ADR, e.g. COMPLIANT with
            # nothing to cite; keep looking for an exact obligation match before settling on it.
            if not quote and got is None:
                got = str(f.get("verdict"))
        # A COMPLIANT case asks for silence: the checker raising nothing against that obligation is a hit.
        # Any other expectation needs the finding to be there.
        if got is None:
            outcome = "quiet" if case.expected == "COMPLIANT" else "absent"
        else:
            outcome = "hit" if got == case.expected else "miss"
        rows.append(CaseResult(case, outcome, got))
        matrix[(case.expected, got)] += 1
    return Score(tuple(rows), matrix)
