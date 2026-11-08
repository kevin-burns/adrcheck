"""Rows a team has reviewed and chosen to carry: the brownfield baseline.

A repository adopting adrcheck has history. Its first stale sweep lists every accepted ADR whose
anchors have left the tree, and most of those rows are renames or accepted debt, not news. The
baseline names the rows already reviewed so that later reports can set them aside and show only
what changed. It is a value: how it is stored is an adapter's business.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Baseline:
    stale: frozenset[tuple[int, str]] = frozenset()  # (adr number, obligation id)

    def knows(self, adr_number: int, obligation_id: str) -> bool:
        return (adr_number, obligation_id) in self.stale


EMPTY = Baseline()
