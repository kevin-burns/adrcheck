"""`.adrcheck/map.toml`: `[[adr]] id = 4  paths = ["enrich/**"]`, the same glob subset as `Applies to`."""

from __future__ import annotations

import tomllib
from pathlib import Path


def load_scope_map(path: Path) -> dict[int, tuple[str, ...]]:
    if not Path(path).exists():
        return {}
    data = tomllib.loads(Path(path).read_text())
    return {int(row["id"]): tuple(str(p) for p in row.get("paths", ())) for row in data.get("adr", ())}
