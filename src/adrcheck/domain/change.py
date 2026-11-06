"""One change under review: a commit or staged diff, as the lines it added and removed."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Line:
    path: str
    kind: Literal["+", "-"]
    number: int
    text: str


@dataclass(frozen=True)
class FileChange:
    path: str
    old_path: str | None
    added: tuple[Line, ...] = ()
    removed: tuple[Line, ...] = ()

    def lines(self) -> tuple[Line, ...]:
        return self.added + self.removed


@dataclass(frozen=True)
class Change:
    ref: str
    message: str
    parent: str | None = None
    files: tuple[FileChange, ...] = ()

    def paths(self) -> tuple[str, ...]:
        return tuple(f.path for f in self.files)

    def touched(self, path: str, text: str, kinds: tuple[str, ...] = ("+", "-")) -> bool:
        """True when the change added or removed a line with this text in this file.

        Indentation is ignored on both sides: models drop it when they copy a line. A leading
        diff marker ("+ " or "- ") that a model copied along with the line is tolerated too,
        but only if the bare line does not match on its own, so a line that really starts
        with "-" (a markdown bullet, a negative number) is still compared as written.
        """
        wanted = text.strip()
        candidates = {wanted}
        if wanted[:1] in "+-" and wanted[1:].strip():
            candidates.add(wanted[1:].strip())
        return any(
            line.text.strip() in candidates
            for f in self.files
            if f.path == path
            for line in f.lines()
            if line.kind in kinds
        )
