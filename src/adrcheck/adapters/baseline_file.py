"""The baseline on disk: `.adrcheck/baseline.json`, reviewed like source and never rewritten by accident."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from adrcheck.domain.baseline import Baseline
from adrcheck.usecases.check import StaleAdr

FORMAT_VERSION = 1


def load_baseline(path: Path) -> Baseline:
    if not Path(path).exists():
        return Baseline()
    data = json.loads(Path(path).read_text())
    return Baseline(stale=frozenset((int(r["adr"]), str(r["obligation"])) for r in data.get("stale", ())))


def write_baseline(path: Path, stale: Iterable[StaleAdr]) -> None:
    """Every stale row of the run, known or not, so the file is the full reviewed list and not a delta."""
    rows = [{"adr": s.adr_number, "obligation": s.obligation_id, "missing": list(s.missing)} for s in stale]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps({"version": FORMAT_VERSION, "stale": rows}, indent=1) + "\n")
