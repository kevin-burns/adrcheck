"""Commits as Changes, and the parent-snapshot probes, via the git CLI."""

from __future__ import annotations

import io
import re
import subprocess  # nosec B404 - argv-list calls only, see GitRepo._git
import tokenize
from pathlib import Path

from adrcheck.adapters.unified_diff import parse_patch
from adrcheck.domain.change import Change

_SEP = "\x1e"
STAGED = "STAGED"  # the ref name a pre-commit run uses for the index; its parent is HEAD
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
        self._code_cache: dict[str, dict[str, str]] = {}

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        # errors="replace": a binary blob in the tree (an icon, a font, a parquet file) must not end the run.
        return subprocess.run(  # nosec B603 B607 - argv list, no shell, fixed executable
            ["git", "-C", str(self.root), *args],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def rev_parse(self, spec: str) -> str:
        return self._git("rev-parse", "--verify", f"{spec}^{{commit}}").stdout.strip()

    def ls(self, ref: str, directory: str) -> list[str]:
        """Paths under `directory` at `ref`; empty when the directory or the ref does not exist."""
        out = self._git("ls-tree", "-r", "--name-only", ref, "--", directory.rstrip("/") + "/", check=False)
        return [p for p in out.stdout.split("\n") if p] if out.returncode == 0 else []

    def blob(self, ref: str, path: str) -> str:
        """The blob id of `path` at `ref`, as `git rev-parse ref:path` prints it."""
        return self._git("rev-parse", f"{ref}:{path}").stdout.strip()

    def read(self, ref: str, path: str) -> str:
        # STAGED is the index: `git show :path`. Everything else is a commit-ish.
        return self._git("show", f"{'' if ref == STAGED else ref}:{path}").stdout

    def _code_files(self, ref: str) -> dict[str, str] | None:
        """Path -> code text at `ref`, prose files skipped, Python comments and docstrings blanked. Cached per ref.
        Every path in the tree is a key, prose files with empty text, so a path anchor is found by name."""
        key = f"{self.root}@{ref}"
        if key in self._code_cache:
            return self._code_cache[key]
        listing = (
            self._git("ls-files", "--cached", check=False)
            if ref == STAGED
            else self._git("ls-tree", "-r", "--name-only", ref, check=False)
        )
        if listing.returncode != 0:
            return None
        # .adrcheck/ holds the compiled obligations, which name every anchor: reading it as code would make the
        # stale sweep blind to the very ADRs it checks on a repository that commits the cache.
        paths = [p for p in listing.stdout.split("\n") if p and not p.startswith(".adrcheck/")]
        files: dict[str, str] = dict.fromkeys(paths, "")
        wanted = [p for p in paths if not p.lower().endswith(_PROSE)]
        for path, text in self._blobs(ref, wanted).items():
            files[path] = strip_python_prose(text) if path.endswith(".py") else text
        self._code_cache[key] = files
        return files

    def _code_text(self, ref: str) -> str | None:
        """All code at `ref` as one string; file paths are in it too, so an ADR may name a module."""
        files = self._code_files(ref)
        if files is None:
            return None
        return "\n".join(["\n".join(files), *files.values()])

    def has_line(self, ref: str, text: str) -> bool | None:
        files = self._code_files(ref)
        if files is None:
            return None
        pattern = re.compile(rf"^[ \t]*{re.escape(text.strip())}[ \t]*$", re.MULTILINE)
        return any(pattern.search(body) for body in files.values())

    def locate(self, ref: str, needle: str) -> list[str] | None:
        files = self._code_files(ref)
        if files is None:
            return None
        pattern = re.compile(rf"(?<![\w.]){re.escape(needle)}(?!\w)") if needle.isidentifier() else None
        hit = [
            p
            for p, text in files.items()
            if p == needle or needle in p or (pattern.search(text) if pattern else needle in text)
        ]
        return sorted(hit)

    def _blobs(self, ref: str, paths: list[str]) -> dict[str, str]:
        """Every blob in one `git cat-file --batch` process; one `git show` per file cost 17 ms a file (bead zsj)."""
        if not paths:
            return {}
        prefix = "" if ref == STAGED else ref
        request = "".join(f"{prefix}:{p}\n" for p in paths).encode("utf-8")
        proc = subprocess.run(  # nosec B603 B607 - argv list, no shell
            ["git", "-C", str(self.root), "cat-file", "--batch"], input=request, capture_output=True, check=False
        )
        out, pos, blobs = proc.stdout, 0, {}
        for path in paths:
            nl = out.find(b"\n", pos)
            if nl < 0:
                break
            header = out[pos:nl].split()
            pos = nl + 1
            if len(header) != 3:  # "<spec> missing", or an ambiguous object: nothing to read for this path
                continue
            size = int(header[2])
            blobs[path] = out[pos : pos + size].decode("utf-8", errors="replace")
            pos += size + 1  # the trailing newline cat-file appends after each object
        return blobs

    def contains(self, ref: str, needle: str) -> bool | None:
        code = self._code_text(ref)
        return None if code is None else needle in code

    def occurrences(self, ref: str, needle: str) -> int | None:
        """Whole-identifier count over file contents only. The path listing is in `_code_text` for `contains()`,
        so an ADR may name a module, but a module named after its function is not a call of that function."""
        files = self._code_files(ref)
        if files is None:
            return None
        pattern = re.compile(rf"(?<![\w.]){re.escape(needle)}(?!\w)")
        return sum(len(pattern.findall(text)) for text in files.values())


class GitChanges(GitRepo):
    def changes(self, spec: str) -> list[Change]:
        revs = self._git("rev-list", "--reverse", "--no-merges", spec).stdout.split()
        return [self._change(rev) for rev in revs]

    def staged(self) -> Change:
        """The index as one Change: what a pre-commit hook is about to commit, with HEAD as the parent."""
        head = self._git("rev-parse", "--verify", "-q", "HEAD", check=False).stdout.strip() or None
        patch = self._git("diff", "--cached", "--no-color", "--find-renames", "--patch").stdout
        # pre-commit runs before git writes the new message, so COMMIT_EDITMSG usually still holds the previous
        # commit's text; reading it would carry a waiver forward (ADR-6: per commit). Only a file newer than HEAD
        # counts.
        msg_file = self.root / ".git" / "COMMIT_EDITMSG"
        message = ""
        if msg_file.exists() and head:
            head_time = int(self._git("log", "-1", "--format=%ct", head).stdout.strip() or 0)
            if msg_file.stat().st_mtime > head_time:
                message = msg_file.read_text()
        return Change(ref=STAGED, parent=head, message=message.strip("\n"), files=parse_patch(patch))

    def combined(self, spec: str) -> Change:
        """A range as the one change it merges (ADR-13): parent is the merge base, files are the net diff, and the
        message carries every commit's message so an Adr-Exception trailer on any of them counts. A line added
        in one commit and removed in a later one is not part of the change at all."""
        base_spec, _, head_spec = spec.partition("..")
        head = self._git("rev-parse", head_spec or "HEAD").stdout.strip()
        base = self._git("merge-base", base_spec, head).stdout.strip()
        patch = self._git("diff", "--no-color", "--find-renames", "--patch", base, head).stdout
        messages = self._git("log", "--reverse", "--no-merges", f"--format=%B{_SEP}", f"{base}..{head}").stdout
        message = "\n\n".join(m.strip("\n") for m in messages.split(_SEP) if m.strip())
        return Change(ref=head, parent=base, message=message, files=parse_patch(patch))

    def _change(self, rev: str) -> Change:
        meta = self._git("show", "-s", f"--format=%P{_SEP}%B", rev).stdout
        parents, _, message = meta.partition(_SEP)
        parent = parents.split()[0] if parents.split() else None
        patch = self._git("show", "--format=", "--no-color", "--patch", "--find-renames", rev).stdout
        return Change(ref=rev, parent=parent, message=message.strip("\n"), files=parse_patch(patch))
