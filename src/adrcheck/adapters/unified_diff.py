"""Turn a unified diff (git show / git diff output) into FileChange records."""

from __future__ import annotations

import re

from adrcheck.domain.change import FileChange, Line

_FILE = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_patch(text: str) -> tuple[FileChange, ...]:
    files: list[FileChange] = []
    path: str | None = None
    old_path: str | None = None
    added: list[Line] = []
    removed: list[Line] = []
    old_no = new_no = 0

    def close() -> None:
        if path is not None:
            files.append(FileChange(path=path, old_path=old_path, added=tuple(added), removed=tuple(removed)))

    for raw in text.splitlines():
        if m := _FILE.match(raw):
            close()
            old_path, path = m.group(1), m.group(2)
            added, removed = [], []
            continue
        if path is None:
            continue
        if raw.startswith("--- "):
            if raw == "--- /dev/null":
                old_path = None
            continue
        if raw.startswith("+++ ") or raw.startswith("index ") or raw.startswith(("new file", "deleted file", "similarity", "rename ", "old mode", "new mode", "Binary files")):
            continue
        if m := _HUNK.match(raw):
            old_no, new_no = int(m.group(1)), int(m.group(2))
            continue
        if raw.startswith("+"):
            added.append(Line(path=path, kind="+", number=new_no, text=raw[1:]))
            new_no += 1
        elif raw.startswith("-"):
            removed.append(Line(path=path, kind="-", number=old_no, text=raw[1:]))
            old_no += 1
        elif raw.startswith("\\"):
            continue
        else:
            old_no += 1
            new_no += 1
    close()
    return tuple(files)
