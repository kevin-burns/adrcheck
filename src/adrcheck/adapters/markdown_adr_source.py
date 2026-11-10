"""ADRs from the markdown files in one directory (ADR-12): every .md is a record unless it is the directory's
README, index or template. The number comes from the title, then the filename; a record with neither is kept
and lint reports it."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from adrcheck.adapters.git_changes import GitRepo
from adrcheck.adapters.markdown_adr import parse_adr
from adrcheck.domain.adr import Adr

_NOT_A_RECORD = re.compile(r"^(readme|index|template)(\..*)?\.md$", re.IGNORECASE)


def git_blob_id(data: bytes) -> str:
    """What `git hash-object` prints for these bytes: sha1 over `blob <size>\\0` and the content. The same id as the
    committed file carries, so `git log --find-object <id>` names the commits that hold exactly this text."""
    return hashlib.sha1(b"blob %d\0%s" % (len(data), data), usedforsecurity=False).hexdigest()


def is_record(name: str) -> bool:
    return name.lower().endswith(".md") and not _NOT_A_RECORD.match(name)


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
        files = sorted(p for p in self.directory.iterdir() if p.is_file() and is_record(p.name))
        return [parse_adr(p.read_text(), source=str(p), blob=git_blob_id(p.read_bytes())) for p in files]


def adrs_at(repo: GitRepo, ref: str, adr_dir: str) -> list[Adr]:
    """The ADR directory as it stood at `ref`: what an eval corpus frozen at that revision was labelled against."""
    paths = sorted(p for p in repo.ls(ref, adr_dir) if is_record(Path(p).name))
    return [parse_adr(repo.read(ref, p), source=f"{ref}:{p}", blob=repo.blob(ref, p)) for p in paths]
