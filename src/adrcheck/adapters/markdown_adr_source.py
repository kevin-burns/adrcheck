"""ADRs from numbered markdown files in one directory."""

from __future__ import annotations

import re
from pathlib import Path

from adrcheck.adapters.markdown_adr import parse_adr
from adrcheck.domain.adr import Adr

_NUMBERED = re.compile(r"^\d+.*\.md$")

# Where teams keep ADRs, most specific first: Nygard's docs/adr, MADR's docs/decisions, adr-tools'
# docs/architecture/decisions, then the shorter variants.
CONVENTIONAL_DIRS = (
    "docs/adr",
    "docs/decisions",
    "docs/architecture/decisions",
    "doc/adr",
    "doc/architecture/decisions",
    "adr",
    "adrs",
    "decisions",
)


def discover_adr_dir(repo: Path) -> Path | None:
    """The first conventional ADR directory that exists under the repository root, or None."""
    for rel in CONVENTIONAL_DIRS:
        candidate = Path(repo) / rel
        if candidate.is_dir():
            return candidate
    return None


class MarkdownAdrSource:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def adrs(self) -> list[Adr]:
        files = sorted(p for p in self.directory.iterdir() if _NUMBERED.match(p.name))
        return [parse_adr(p.read_text(), source=str(p)) for p in files]
