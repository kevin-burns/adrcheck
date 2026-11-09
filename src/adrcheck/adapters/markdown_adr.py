"""Parse markdown ADRs of any common shape into an Adr. The format is a detail; callers see only Adr.

Bind on ROLES, not on headings. Every heading, bold label, table row or `Label:` line is mapped through
one alias table to a canonical section: decision, consequences, context, drivers, options, confirmation,
notes, status. The binding roles (decision, consequences) are what verify() and the compiler read; the
rejected role (options) can never bind; a shape that lacks a role leaves it absent rather than guessed.
"""

from __future__ import annotations

import re
from pathlib import PurePath

from adrcheck.domain.adr import Adr, Status

_TITLE = re.compile(r"^#\s+(?:(?:ADR[- ]?)?(\d+)[.:]?\s+)?(.+?)\s*$", re.IGNORECASE)
_HEADER_LINE = re.compile(r"^([A-Za-z][A-Za-z ]*):\s*(.*)$")
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_SUBHEADING = re.compile(r"^###\s+(.+?)\s*$")  # opens a section only when its name is a known role (MADR nests)
_BOLD_LABEL = re.compile(r"^\*\*([A-Za-z][A-Za-z /&-]*?):?\*\*:?\s*(.*)$")
_TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$")
_ADR_REF = re.compile(r"ADR[- ]?0*(\d+)", re.IGNORECASE)
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")  # [text](target), not images
_Y_STATEMENT = re.compile(
    r"in the context of\s+(?P<context>.+?),\s*facing\s+(?P<problem>.+?),\s*"
    r"we decided (?:for|on)\s+(?P<decision>.+?)"
    r"(?:\s+and neglected\s+(?P<options>.+?))?"
    r",?\s*to achieve\s+(?P<drivers>.+?)"
    r"(?:,\s*accepting(?: that)?\s+(?P<consequences>.+?))?\.?\s*$",
    re.IGNORECASE | re.DOTALL,
)

# Heading or label (lower-case) -> canonical section. Section NAMES only, from the common templates:
# Nygard, MADR 4, Tyree and Akerman, arc42 section 9, the Alexandrian pattern form, Planguage, business
# case, ITD, EdgeX, and house styles. A name absent here keeps its own lower-case key and binds nothing.
ROLES: dict[str, str] = {
    # binding: the decision itself
    "decision": "decision",
    "decision outcome": "decision",
    "outcome": "decision",
    "resolution": "decision",
    "solution": "decision",
    "therefore": "decision",
    "recommendation": "decision",
    "proposed design": "decision",
    "must": "decision",
    # binding: what follows from it
    "consequences": "consequences",
    "positive consequences": "consequences",
    "negative consequences": "consequences",
    "resulting context": "consequences",
    "implications": "consequences",
    "costs": "consequences",
    "benefits": "consequences",
    "risks": "consequences",
    # intent: why
    "context": "context",
    "context and problem statement": "context",
    "problem": "context",
    "problem statement": "context",
    "issue": "context",
    "background": "context",
    "motivation": "context",
    "gist": "context",
    "rationale": "context",
    "justification": "context",
    "argument": "context",
    "arguments": "context",
    "assumptions": "context",
    "constraints": "context",
    "forces": "context",
    "decision drivers": "drivers",
    "drivers": "drivers",
    # rejected: never binds; a quote from here is evidence of NOT deciding
    "considered options": "options",
    "considered alternatives": "options",
    "options": "options",
    "options considered": "options",
    "alternatives": "options",
    "positions": "options",
    "pros and cons of the options": "options",
    "neglected": "options",
    # process: obligations on people, not code
    "confirmation": "confirmation",
    "action items": "confirmation",
    "more information": "notes",
    "notes": "notes",
    "references": "notes",
    "related decisions": "notes",
    "related requirements": "notes",
    "related patterns": "notes",
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
    return fields, text[m.end() :]


def _role(label: str) -> str | None:
    return ROLES.get(label.strip().lower())


def parse_adr(text: str, source: str) -> Adr:
    headers, text = _front_matter(text)
    lines = text.splitlines()
    title, number = "", None
    sections: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    saw_heading = False

    def close() -> None:
        if current is not None:
            chunk = "\n".join(body).strip()
            sections[current] = f"{sections[current]}\n\n{chunk}".strip() if current in sections else chunk

    def open_section(key: str, first_line: str = "") -> None:
        nonlocal current, body
        close()
        current, body = key, [first_line] if first_line else []

    def one_liner(key: str, value: str) -> None:
        nonlocal current
        open_section(key, value)
        close()
        current = None

    for line in lines:
        if current is None and not title and (m := _TITLE.match(line)):
            number = int(m.group(1)) if m.group(1) else None
            title = m.group(2)
            continue
        if m := _HEADING.match(line):
            saw_heading = True
            key = m.group(1).strip().lower()
            open_section(_role(key) or key)
            continue
        if (m := _SUBHEADING.match(line)) and (role := _role(m.group(1))):
            open_section(role)
            continue
        if (m := _BOLD_LABEL.match(line)) and (role := _role(m.group(1))):
            if role == "status":
                headers["status"] = m.group(2).strip()
            else:
                open_section(role, m.group(2))
            continue
        if (m := _TABLE_ROW.match(line)) and (role := _role(m.group(1))):
            if role == "status":
                headers["status"] = m.group(2).strip()
            else:
                one_liner(role, m.group(2))
            continue
        if not saw_heading and current is None and (m := _HEADER_LINE.match(line)):
            label, value = m.group(1).strip().lower(), m.group(2).strip()
            role = _role(label)
            if role and role != "status":
                one_liner(role, value)  # Planguage and other label-line shapes: `Must: ...` is the decision
            else:
                headers[label] = value
            continue
        if current is None:
            if not saw_heading and line.strip():
                open_section("y-statement", line)  # prose before any heading: a Y-statement, or a preamble
            continue
        body.append(line)
    close()

    preamble = sections.pop("y-statement", "")
    if preamble and "decision" not in sections and (m := _Y_STATEMENT.search(" ".join(preamble.split()))):
        for role in ("context", "decision", "options", "drivers", "consequences"):
            if m.group(role):
                sections[role] = m.group(role).strip()
        if m.group("problem"):
            sections["context"] = f"{sections.get('context', '')}; facing {m.group('problem').strip()}".strip("; ")

    if number is None and (m := re.match(r"(\d+)", PurePath(source).name)):
        number = int(m.group(1))
    status_text = headers.get("status") or sections.get("status", "")
    applies = headers.get("applies to", "")
    applies_to = tuple(p.strip() for p in applies.split(",") if p.strip())
    supersedes = tuple(int(n) for n in _ADR_REF.findall(headers.get("supersedes", "")))
    depends_on = tuple(int(n) for n in _ADR_REF.findall(headers.get("depends on", "")))
    links = tuple(
        dict.fromkeys(t for t in _LINK.findall(text) if not t.startswith(("#", "http://", "https://", "mailto:", "/")))
    )
    superseded_by = (
        tuple(int(n) for n in _ADR_REF.findall(status_text)) if Status.parse(status_text) is Status.SUPERSEDED else ()
    )
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
        depends_on=depends_on,
        links=links,
    )
