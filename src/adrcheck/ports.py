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
class JudgeResponse:
    relevant: bool
    findings: tuple[RawFinding, ...] = ()
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


class AdrSource(Protocol):
    def adrs(self) -> list[Adr]: ...


class ChangeSource(Protocol):
    def changes(self, spec: str) -> list[Change]: ...


class RepoReader(Protocol):
    def read(self, ref: str, path: str) -> str: ...

    def contains(self, ref: str, needle: str) -> bool | None:
        """Does `needle` occur anywhere in the tree at `ref`? None when the probe cannot run."""
        ...


class ObligationCompiler(Protocol):
    def compile(self, adr: Adr) -> tuple[Obligation, ...]: ...


class ChangeJudge(Protocol):
    def judge(
        self, change: Change, adr: Adr, obligations: tuple[Obligation, ...], context: Context
    ) -> JudgeResponse: ...
