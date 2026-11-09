"""Explain one ADR: its obligations, and for each anchor where it lives in the code at a ref. The architect's
question, "is this decision still true and where", answered without a judge call. Compile is the cached one.
No I/O of its own."""

from __future__ import annotations

from dataclasses import dataclass

from adrcheck.domain.adr import Adr
from adrcheck.domain.obligation import Obligation
from adrcheck.ports import ObligationCompiler, RepoReader


@dataclass(frozen=True)
class AnchorStatus:
    name: str
    forbidden: bool  # from `forbids`; files holding it are the finding, not the comfort
    files: tuple[str, ...] | None  # None: the ref could not be read
    count: int | None  # whole-identifier occurrences; None when not an identifier or unreadable


@dataclass(frozen=True)
class ObligationStatus:
    obligation: Obligation
    anchors: tuple[AnchorStatus, ...]

    @property
    def stale(self) -> bool | None:
        """Every mandated anchor gone, as the stale sweep would see it (ADR-5). None when the ref is unreadable;
        False when the obligation mandates nothing."""
        mandated = [a for a in self.anchors if not a.forbidden]
        if any(a.files is None for a in mandated):
            return None
        return bool(mandated) and all(not a.files for a in mandated)


def explain(adr: Adr, compiler: ObligationCompiler, repo: RepoReader, ref: str) -> list[ObligationStatus]:
    out: list[ObligationStatus] = []
    for o in compiler.compile(adr):
        anchors = [_status(repo, ref, n, forbidden=False) for n in o.mandates]
        anchors += [_status(repo, ref, n, forbidden=True) for n in o.forbids]
        out.append(ObligationStatus(o, tuple(anchors)))
    return out


def _status(repo: RepoReader, ref: str, name: str, *, forbidden: bool) -> AnchorStatus:
    files = repo.locate(ref, name)
    count = repo.occurrences(ref, name) if name.isidentifier() else None
    return AnchorStatus(name, forbidden, None if files is None else tuple(files), count)
