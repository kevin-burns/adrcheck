"""ADRs from numbered markdown files in one directory."""

from __future__ import annotations

import re
from pathlib import Path

from adrcheck.adapters.markdown_adr import parse_adr
from adrcheck.domain.adr import Adr

_NUMBERED = re.compile(r"^\d+.*\.md$")


class MarkdownAdrSource:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def adrs(self) -> list[Adr]:
        files = sorted(p for p in self.directory.iterdir() if _NUMBERED.match(p.name))
        return [parse_adr(p.read_text(), source=str(p)) for p in files]
