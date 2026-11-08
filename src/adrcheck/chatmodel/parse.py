"""Reply parsers for the two seats. Strict: a quote not in the binding text drops the obligation; an
unparseable judge reply is an error, never a verdict."""

from __future__ import annotations

import json
import re

from adrcheck.domain.adr import Adr
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.verdict import Verdict
from adrcheck.domain.verify import BINDING_SECTIONS
from adrcheck.ports import JudgeResponse, RawFinding


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if m := re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
        text = m.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return None
        text = text[start : end + 1]
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def parse_compile_reply(reply: str, adr: Adr) -> tuple[Obligation, ...]:
    data = _extract_json(reply)
    if not data:
        return ()
    binding = " ".join(" ".join(adr.section(s).split()) for s in BINDING_SECTIONS)
    adr_text = adr.title + " " + " ".join(adr.sections.values())
    out: list[Obligation] = []
    for item in data.get("obligations", []):
        quote = " ".join(str(item.get("quote", "")).split())
        if not quote or quote not in binding:
            continue
        try:
            checkability = Checkability(str(item.get("checkability", "intent")).lower())
        except ValueError:
            checkability = Checkability.INTENT
        kind = "MUST_NOT" if str(item.get("kind", "MUST")).upper().replace(" ", "_") == "MUST_NOT" else "MUST"
        out.append(
            Obligation(
                id=f"ADR-{adr.number}/{len(out) + 1}",
                adr_number=adr.number or 0,
                kind=kind,
                text=str(item.get("text", "")).strip(),
                quote=quote,
                checkability=checkability,
                mandates=_anchor_names(item.get("mandates", []) or [], adr_text),
                forbids=tuple(str(x) for x in item.get("forbids", []) or []),
            )
        )
    return tuple(out)


_FILE_EXTENSIONS = (
    ".py",
    ".pyi",
    ".ts",
    ".tsx",
    ".js",
    ".go",
    ".rs",
    ".java",
    ".cs",
    ".sh",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
)


def _anchor_names(raw: list, adr_text: str) -> tuple[str, ...]:
    """Mandates as the code spells them.

    Prose says `RepoReader.contains()`; code says `repo.contains` on a RepoReader-typed parameter, so the
    dotted form is probed as its bare names. A path keeps its dots. An anchor the ADR does not name is the
    compiler's invention; absence of an invented anchor must never make an ADR look overtaken.
    """
    out: list[str] = []
    for x in raw:
        text = str(x).strip().removesuffix("()")
        if not text:
            continue
        is_path = "/" in text or text.lower().endswith(_FILE_EXTENSIONS)
        for name in [text] if is_path else text.split("."):
            if name and name in adr_text and name not in out:
                out.append(name)
    return tuple(out)


def parse_judge_reply(reply: str) -> JudgeResponse:
    data = _extract_json(reply)
    if data is None or "findings" not in data:
        return JudgeResponse(error=f"unparseable judge reply: {reply[:120]!r}")
    findings = []
    for item in data.get("findings", []) or []:
        try:
            verdict = Verdict(str(item.get("verdict", "UNCLEAR")).upper())
        except ValueError:
            verdict = Verdict.UNCLEAR
        findings.append(
            RawFinding(
                obligation_id=str(item.get("obligation_id", "")),
                verdict=verdict,
                path=str(item.get("path", "")),
                line_text=str(item.get("line_text", "")),
                quote=str(item.get("quote", "")),
                reason=str(item.get("reason", "")),
            )
        )
    not_relevant = frozenset(int(n) for n in data.get("not_relevant", []) or [] if str(n).strip().isdigit())
    return JudgeResponse(findings=tuple(findings), not_relevant=not_relevant)
