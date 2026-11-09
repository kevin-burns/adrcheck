"""Interfaces the use cases need. Inner layers own them; adapters implement them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from adrcheck.domain.adr import Adr
from adrcheck.domain.change import Change
from adrcheck.domain.obligation import Obligation
from adrcheck.domain.verdict import Verdict


@dataclass(frozen=True)
class RawFinding:
    """The judge's unverified claim about one obligation."""

    obligation_id: str
    verdict: Verdict
    path: str
    line_text: str
    quote: str
    reason: str


@dataclass(frozen=True)
class JudgeCase:
    """One ADR and its checkable obligations, to be judged against a change."""

    adr: Adr
    obligations: tuple[Obligation, ...]


@dataclass(frozen=True)
class JudgeResponse:
    """One answer for every case of a change. The diff is the cost, so it travels once; the adapter decides
    how many model calls that takes."""

    findings: tuple[RawFinding, ...] = ()
    not_relevant: frozenset[int] = frozenset()  # ADR numbers the judge says the change has nothing to do with
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    error: str = ""


@dataclass(frozen=True)
class Context:
    """What the judge is shown beyond the diff. Budgeted by the use case."""

    post_images: dict[str, str]
    module_map: str = ""


class NotCompiled(Exception):
    """Raised by a cache-only compiler when an ADR has no cached obligations. The free tier never compiles."""

    def __init__(self, adr):
        super().__init__(f"ADR-{adr.number} not compiled")
        self.adr = adr


class AdrSource(Protocol):
    def adrs(self) -> list[Adr]: ...


class ChangeSource(Protocol):
    def changes(self, spec: str) -> list[Change]: ...


class RepoReader(Protocol):
    def read(self, ref: str, path: str) -> str: ...

    def contains(self, ref: str, needle: str) -> bool | None:
        """Does `needle` occur anywhere in the tree at `ref`? None when the probe cannot run."""
        ...

    def occurrences(self, ref: str, needle: str) -> int | None:
        """How many times `needle` occurs as a whole identifier in the code at `ref`. A definition counts once;
        so a count of one means nothing used it. None when the probe cannot run."""
        ...

    def has_line(self, ref: str, text: str) -> bool | None:
        """Does `text`, stripped, occur as a whole line of code at `ref`? The precedent question: a substring hit
        inside a longer line or a string literal is not the same line. None when the ref cannot be read."""
        ...

    def locate(self, ref: str, needle: str) -> list[str] | None:
        """Sorted paths of code files at `ref` whose text holds `needle`; a path anchor locates itself. None when
        the ref cannot be read."""
        ...


class ObligationCompiler(Protocol):
    def compile(self, adr: Adr) -> tuple[Obligation, ...]: ...


class ChangeJudge(Protocol):
    def judge(self, change: Change, cases: tuple[JudgeCase, ...], context: Context) -> JudgeResponse: ...
