"""Parse Nygard and MADR markdown into an Adr. The format is a detail; callers see only Adr."""

from __future__ import annotations

import re
from pathlib import PurePath

from adrcheck.domain.adr import Adr, Status

_TITLE = re.compile(r"^#\s+(?:(?:ADR[- ]?)?(\d+)[.:]?\s+)?(.+?)\s*$", re.IGNORECASE)
_HEADER_LINE = re.compile(r"^([A-Za-z][A-Za-z ]*):\s*(.*)$")
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_ADR_REF = re.compile(r"ADR[- ]?0*(\d+)", re.IGNORECASE)
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

_CANONICAL = {
    "context": "context",
    "context and problem statement": "context",
    "decision": "decision",
    "decision outcome": "decision",
    "consequences": "consequences",
    "status": "status",
}


def _front_matter(text: str) -> tuple[dict[str, str], str]:
    """Minimal YAML front matter: scalars and simple `- item` lists. Enough for ADR headers."""
    m = _FRONT_MATTER.match(text)
    if not m:
        return {}, text
    fields: dict[str, str] = {}
    key = None
    for raw in m.group(1).splitlines():
        if raw.startswith(("-", " ")) and key:
            item = raw.strip().lstrip("-").strip().strip("\"'")
            fields[key] = f"{fields[key]}, {item}" if fields[key] else item
        elif ":" in raw:
            key, _, value = raw.partition(":")
            key = key.strip().lower().replace("_", " ")
            fields[key] = value.strip().strip("\"'")
    return fields, text[m.end():]


def parse_adr(text: str, source: str) -> Adr:
    headers, text = _front_matter(text)
    lines = text.splitlines()
    title, number = "", None
    sections: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []

    def close() -> None:
        if current is not None:
            sections[current] = "\n".join(body).strip()

    for line in lines:
        if current is None and not title and (m := _TITLE.match(line)):
            number = int(m.group(1)) if m.group(1) else None
            title = m.group(2)
            continue
        if m := _HEADING.match(line):
            close()
            key = m.group(1).strip().lower()
            current = _CANONICAL.get(key, key)
            body = []
            continue
        if current is None:
            if m := _HEADER_LINE.match(line):
                headers[m.group(1).strip().lower()] = m.group(2).strip()
            continue
        body.append(line)
    close()

    if number is None and (m := re.match(r"(\d+)", PurePath(source).name)):
        number = int(m.group(1))
    status_text = headers.get("status") or sections.get("status", "")
    applies = headers.get("applies to", "")
    applies_to = tuple(p.strip() for p in applies.split(",") if p.strip())
    supersedes = tuple(int(n) for n in _ADR_REF.findall(headers.get("supersedes", "")))
    superseded_by = tuple(int(n) for n in _ADR_REF.findall(status_text)) if Status.parse(status_text) is Status.SUPERSEDED else ()
    return Adr(
        title=title,
        supersedes=supersedes,
        superseded_by=superseded_by,
        status=Status.parse(status_text),
        source=source,
        number=number,
        date=headers.get("date") or None,
        applies_to=applies_to,
        sections=sections,
    )
