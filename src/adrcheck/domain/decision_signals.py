"""A change that looks like a decision nobody wrote down. Diff shape only; no model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from adrcheck.domain.change import Change

_IMPORT = re.compile(r"^\s*(?:import\s+([A-Za-z_][\w]*)|from\s+([A-Za-z_][\w]*)[\w.]*\s+import)")
_HOST = re.compile(r"https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_STDLIB_HINT = {"os", "re", "sys", "json", "time", "math", "pathlib", "typing", "dataclasses", "subprocess", "collections", "itertools", "functools", "datetime", "hashlib", "shutil", "enum", "io", "csv", "logging", "argparse", "html", "urllib", "http", "unittest", "textwrap", "string", "random", "statistics", "tempfile", "glob", "fnmatch", "copy", "abc", "contextlib", "operator", "pprint", "uuid", "base64", "struct", "gzip", "zipfile", "tarfile", "sqlite3", "socket", "threading", "asyncio", "concurrent", "multiprocessing", "queue", "signal", "errno", "platform", "locale", "gettext", "decimal", "fractions", "numbers", "array", "bisect", "heapq", "weakref", "types", "inspect", "ast", "dis", "importlib", "pkgutil", "warnings", "traceback", "atexit", "builtins", "__future__"}


_PROSE = (".md", ".markdown", ".txt", ".rst", ".html", ".htm")


@dataclass(frozen=True)
class DecisionSignal:
    kind: str
    detail: str


def decision_signals(change: Change, present_at_parent: Callable[[str], bool | None]) -> tuple[DecisionSignal, ...]:
    out: list[DecisionSignal] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, detail: str) -> None:
        if (kind, detail) not in seen:
            seen.add((kind, detail))
            out.append(DecisionSignal(kind, detail))

    for f in change.files:
        if f.old_path is None and "/" in f.path:
            top = f.path.split("/", 1)[0] + "/"
            if present_at_parent(top) is False:
                add("new-top-level-module", top)
        for line in f.added:
            if m := _IMPORT.match(line.text):
                name = m.group(1) or m.group(2)
                if name not in _STDLIB_HINT and present_at_parent(name) is False:
                    add("new-dependency", name)
            if f.path.lower().endswith(_PROSE):
                continue
            for host in _HOST.findall(line.text):
                if present_at_parent(host) is False:
                    add("new-external-host", host)
    return tuple(out)
