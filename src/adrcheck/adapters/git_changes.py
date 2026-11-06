"""Commits as Changes, and the parent-snapshot probes, via the git CLI."""

from __future__ import annotations

import io
import subprocess
import tokenize
from pathlib import Path

from adrcheck.adapters.unified_diff import parse_patch
from adrcheck.domain.change import Change

_SEP = "\x1e"
_PROSE = (".md", ".markdown", ".txt", ".rst", ".html", ".htm", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".lock")


def strip_python_prose(source: str) -> str:
    """Blank out comments and standalone string statements (docstrings) so a mention is not a presence.

    A string token that is the whole of a logical line is a docstring or a bare string statement,
    neither of which is code that uses the name. String literals inside expressions stay. Removed
    spans are overwritten with spaces in place, so the spacing of the code that remains is untouched.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return source
    lines = source.splitlines(keepends=True)
    skip_prev = {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING}

    def blank(start: tuple[int, int], end: tuple[int, int]) -> None:
        (r0, c0), (r1, c1) = start, end
        for r in range(r0, r1 + 1):
            line = lines[r - 1]
            a = c0 if r == r0 else 0
            b = c1 if r == r1 else len(line.rstrip("\r\n"))
            lines[r - 1] = line[:a] + " " * (b - a) + line[b:]

    for i, tok in enumerate(tokens):
        if tok.type == tokenize.COMMENT:
            blank(tok.start, tok.end)
        elif tok.type == tokenize.STRING:
            prev = tokens[i - 1].type if i else tokenize.ENCODING
            nxt = tokens[i + 1].type if i + 1 < len(tokens) else tokenize.NEWLINE
            if prev in skip_prev and nxt in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER):
                blank(tok.start, tok.end)
    return "".join(lines)


class GitRepo:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args], check=check, capture_output=True, text=True)

    def read(self, ref: str, path: str) -> str:
        return self._git("show", f"{ref}:{path}").stdout

    _code_cache: dict[str, str] = {}

    def _code_text(self, ref: str) -> str | None:
        """All code at `ref` as one string, with prose files, comments and docstrings removed. Cached per ref."""
        key = f"{self.root}@{ref}"
        if key in self._code_cache:
            return self._code_cache[key]
        listing = self._git("ls-tree", "-r", "--name-only", ref, check=False)
        if listing.returncode != 0:
            return None
        parts: list[str] = [listing.stdout]  # file paths count as presence too: an ADR may name a module
        for path in listing.stdout.split("\n"):
            if not path or path.lower().endswith(_PROSE):
                continue
            blob = self._git("show", f"{ref}:{path}", check=False)
            if blob.returncode != 0:
                continue
            text = blob.stdout
            parts.append(strip_python_prose(text) if path.endswith(".py") else text)
        self._code_cache[key] = joined = "\n".join(parts)
        return joined

    def contains(self, ref: str, needle: str) -> bool | None:
        code = self._code_text(ref)
        return None if code is None else needle in code


class GitChanges(GitRepo):
    def changes(self, spec: str) -> list[Change]:
        revs = self._git("rev-list", "--reverse", "--no-merges", spec).stdout.split()
        return [self._change(rev) for rev in revs]

    def _change(self, rev: str) -> Change:
        meta = self._git("show", "-s", f"--format=%P{_SEP}%B", rev).stdout
        parents, _, message = meta.partition(_SEP)
        parent = parents.split()[0] if parents.split() else None
        patch = self._git("show", "--format=", "--no-color", "--patch", "--find-renames", rev).stdout
        return Change(ref=rev, parent=parent, message=message.strip("\n"), files=parse_patch(patch))
