"""Compiler and judge over `claude -p`. Prompt text is the prototype part of this project.

PROMPT_VERSION keys the obligation cache; bump it whenever a prompt changes.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - argv-list calls only, see run_claude
import tempfile
from collections.abc import Callable

from adrcheck.domain.adr import Adr
from adrcheck.domain.change import Change
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.verdict import Verdict
from adrcheck.domain.verify import BINDING_SECTIONS
from adrcheck.ports import Context, JudgeResponse, RawFinding

PROMPT_VERSION = "2026-11-06.1"
Runner = Callable[[str, str], dict]


def run_claude(prompt: str, model: str) -> dict:
    proc = subprocess.run(  # nosec B603 B607 - argv list, no shell; claude resolved from PATH by design
        ["claude", "-p", "--output-format", "json", "--model", model, "--tools", ""],
        input=prompt,
        capture_output=True,
        text=True,
        check=True,
        cwd=tempfile.gettempdir(),  # a neutral cwd: no project CLAUDE.md or MCP servers join the prompt
    )
    return json.loads(proc.stdout)


def _binding_text(adr: Adr) -> str:
    return "\n\n".join(f"## {s.title()}\n\n{adr.section(s)}" for s in BINDING_SECTIONS if adr.section(s))


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


def compile_prompt(adr: Adr) -> str:
    return f"""You compile an architecture decision record (ADR) into its obligations: the specific things it
requires (MUST) or forbids (MUST_NOT) of the code. Only the Decision and Consequences sections bind;
the Context describes the problem and is given for understanding only.

ADR-{adr.number}: {adr.title}

## Context (not binding)

{adr.section("context")}

{_binding_text(adr)}

Return JSON only, of this shape:
{{"obligations": [{{"kind": "MUST" | "MUST_NOT", "text": "<one sentence, concrete>", "quote": "<verbatim words from Decision or Consequences that this derives from>", "checkability": "mechanical" | "structural" | "intent" | "process", "mandates": ["<identifier, path or symbol that should exist in the code while this holds>"], "forbids": ["<literal code pattern whose presence contradicts this>"]}}]}}

Rules: the quote must be copied verbatim from Decision or Consequences. checkability: mechanical = visible
in a diff alone (an import, a dependency, a path); structural = needs to know module boundaries or
ownership; intent = behavioural or semantic, not visible in code shape; process = a team practice, not
checkable from code. mandates and forbids are literal strings a grep could find; leave them empty when
nothing literal applies. Zero obligations is a valid answer for an ADR that binds nothing."""


def judge_prompt(change: Change, adr: Adr, obligations: tuple[Obligation, ...], context: Context) -> str:
    diff_lines = []
    for f in change.files:
        diff_lines.append(f"### {f.path}" + ("  (new file)" if f.old_path is None else ""))
        for line in f.removed:
            diff_lines.append(f"- {line.text}")
        for line in f.added:
            diff_lines.append(f"+ {line.text}")
    obl = "\n".join(f'- {o.id} [{o.kind}, {o.checkability.value}] {o.text}\n  quote: "{o.quote}"' for o in obligations)
    images = "\n\n".join(f"### {p} (after the change)\n```\n{text}\n```" for p, text in context.post_images.items())
    return f"""You judge whether one code change breaks the obligations of one architecture decision record.
Be precise and conservative: a CONFLICT needs an exact changed line and an exact quote. When the diff does
not settle it, answer UNCLEAR. Do not flag test code unless an obligation is about tests, do not flag
code unrelated to the obligations, and do not infer intent that is not visible.

ADR-{adr.number}: {adr.title}

{_binding_text(adr)}

## Obligations to check

{obl}

## The change ({change.ref})

Commit message:
{change.message}

Changed lines (- removed, + added):
{chr(10).join(diff_lines)}

## Files after the change (for context; only the changed lines above may be cited)

{images or "(none available)"}

Return JSON only:
{{"relevant": true | false, "findings": [{{"obligation_id": "<id from the list>", "verdict": "CONFLICT" | "COMPLIANT" | "UNCLEAR", "path": "<changed file>", "line_text": "<one changed line, copied exactly without the leading + or ->", "quote": "<verbatim words from the ADR Decision or Consequences>", "reason": "<one sentence naming the line and the obligation>"}}]}}

relevant=false means this ADR has nothing to do with this change; then findings is empty. Return one
finding per obligation the change touches; omit obligations it does not touch."""


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
                # An anchor the ADR does not name is the compiler's invention; absence of an
                # invented anchor must never make an ADR look overtaken.
                mandates=tuple(str(x) for x in item.get("mandates", []) or [] if str(x) and str(x) in adr_text),
                forbids=tuple(str(x) for x in item.get("forbids", []) or []),
            )
        )
    return tuple(out)


def parse_judge_reply(reply: str) -> JudgeResponse:
    data = _extract_json(reply)
    if data is None or "relevant" not in data:
        return JudgeResponse(relevant=True, findings=(), error=f"unparseable judge reply: {reply[:120]!r}")
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
    return JudgeResponse(relevant=bool(data.get("relevant", True)), findings=tuple(findings))


def _usage(raw: dict) -> dict:
    u = raw.get("usage", {}) or {}
    return {
        "tokens_in": int(u.get("input_tokens", 0))
        + int(u.get("cache_read_input_tokens", 0))
        + int(u.get("cache_creation_input_tokens", 0)),
        "tokens_out": int(u.get("output_tokens", 0)),
        "cost_usd": float(raw.get("total_cost_usd", 0.0)),
        "latency_ms": int(raw.get("duration_api_ms", 0)),
    }


class ClaudeJudge:
    """Implements both ObligationCompiler and ChangeJudge; one adapter, two roles."""

    def __init__(self, run: Runner = run_claude, model: str = "sonnet"):
        self.run, self.model = run, model
        self.last_usage: dict = {}

    def compile(self, adr: Adr) -> tuple[Obligation, ...]:
        raw = self.run(compile_prompt(adr), self.model)
        self.last_usage = _usage(raw)
        return parse_compile_reply(str(raw.get("result", "")), adr)

    def judge(self, change: Change, adr: Adr, obligations: tuple[Obligation, ...], context: Context) -> JudgeResponse:
        raw = self.run(judge_prompt(change, adr, obligations, context), self.model)
        parsed = parse_judge_reply(str(raw.get("result", "")))
        usage = _usage(raw)
        return JudgeResponse(relevant=parsed.relevant, findings=parsed.findings, error=parsed.error, **usage)
