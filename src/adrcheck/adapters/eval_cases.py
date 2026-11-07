"""Frozen eval cases on disk: one JSON file per corpus under evals/cases/."""

from __future__ import annotations

import json
from pathlib import Path

from adrcheck.usecases.evaluate import Case


def load_cases(path: Path) -> tuple[Case, ...]:
    data = json.loads(Path(path).read_text())
    return tuple(
        Case(
            commit=str(c["commit"]),
            adr=int(c["adr"]),
            quote=str(c["quote"]),
            expected=str(c["expected"]),
            note=str(c.get("note") or ""),
        )
        for c in data["cases"]
    )
