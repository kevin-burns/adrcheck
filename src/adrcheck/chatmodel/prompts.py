"""Prompt text for the two chat-model seats. Policy, not provider: every provider sends the same words.

PROMPT_VERSION keys the obligation cache; bump it whenever the compile prompt changes. The compile prompt is
one user message with no system text, byte-identical to the claude -p era, so existing caches still hold.
"""

from __future__ import annotations

from adrcheck.chatmodel.request import ChatRequest
from adrcheck.domain.adr import Adr
from adrcheck.domain.change import Change
from adrcheck.domain.verify import BINDING_SECTIONS
from adrcheck.ports import Context, JudgeCase

PROMPT_VERSION = "2026-11-07.1"

JUDGE_SYSTEM = """You judge whether one code change breaks the obligations of the architecture decision records (ADRs)
listed below. Judge each ADR on its own. Be precise and conservative: a CONFLICT needs an exact changed line
and an exact quote from that ADR. When the diff does not settle it, answer UNCLEAR. Do not flag test code
unless an obligation is about tests, do not flag code unrelated to the obligations, and do not infer intent
that is not visible.

Return JSON only:
{"not_relevant": [<ADR numbers this change has nothing to do with>], "findings": [{"obligation_id": "<id from the lists>", "verdict": "CONFLICT" | "COMPLIANT" | "UNCLEAR", "path": "<changed file>", "line_text": "<one changed line, copied exactly without the leading + or ->", "quote": "<verbatim words from that ADR's Decision or Consequences>", "reason": "<one sentence naming the line and the obligation>"}]}

The verdict and the reason agree: if the reason says the line keeps the obligation, the verdict is
COMPLIANT; if it says the line breaks it, CONFLICT; if the diff does not settle it, UNCLEAR. Never a verdict
the reason withdraws.

An ADR in not_relevant gets no findings. For every other ADR, return one finding per obligation the change
touches and omit obligations it does not touch; an ADR with no touched obligation is simply absent from
findings and from not_relevant."""


def _binding_text(adr: Adr) -> str:
    return "\n\n".join(f"## {s.title()}\n\n{adr.section(s)}" for s in BINDING_SECTIONS if adr.section(s))


def compile_request(adr: Adr) -> ChatRequest:
    return ChatRequest(
        system="",
        user=f"""You compile an architecture decision record (ADR) into its obligations: the specific things it
requires (MUST) or forbids (MUST_NOT) of the code. Only the Decision and Consequences sections bind;
the Context describes the problem and is given for understanding only.

ADR-{adr.number}: {adr.title}

## Context (not binding)

{adr.section("context")}

{_binding_text(adr)}

Return JSON only, of this shape:
{{"obligations": [{{"kind": "MUST" | "MUST_NOT", "text": "<one sentence, concrete>", "quote": "<verbatim words from Decision or Consequences that this derives from>", "checkability": "mechanical" | "structural" | "intent" | "process", "mandates": ["<a name as the code spells it: one bare identifier, or one file path>"], "forbids": ["<literal code pattern whose presence contradicts this>"]}}]}}

Rules: the quote must be copied verbatim from Decision or Consequences. checkability: mechanical = visible
in a diff alone (an import, a dependency, a path); structural = needs to know module boundaries or
ownership; intent = behavioural or semantic, not visible in code shape; process = a team practice, not
checkable from code. mandates and forbids are literal strings a grep could find; leave them empty when
nothing literal applies. A mandate is a bare identifier (`contains`, `RepoReader`) or a file path, never a
dotted `Class.method` or a call with parentheses: prose spells `RepoReader.contains()`, code spells
`repo.contains`. Zero obligations is a valid answer for an ADR that binds nothing.""",
    )


def judge_request(change: Change, cases: tuple[JudgeCase, ...], context: Context) -> ChatRequest:
    diff_lines = []
    for f in change.files:
        diff_lines.append(f"### {f.path}" + ("  (new file)" if f.old_path is None else ""))
        for line in f.removed:
            diff_lines.append(f"- {line.text}")
        for line in f.added:
            diff_lines.append(f"+ {line.text}")
    blocks = []
    for case in cases:
        obl = "\n".join(
            f'- {o.id} [{o.kind}, {o.checkability.value}] {o.text}\n  quote: "{o.quote}"' for o in case.obligations
        )
        blocks.append(
            f"## ADR-{case.adr.number}: {case.adr.title}\n\n{_binding_text(case.adr)}\n\n### Obligations of ADR-{case.adr.number}\n\n{obl}"
        )
    adr_blocks = "\n\n".join(blocks)
    numbers = ", ".join(str(c.adr.number) for c in cases)
    images = "\n\n".join(f"### {p} (after the change)\n```\n{text}\n```" for p, text in context.post_images.items())
    user = f"""# ADRs under judgement: {numbers}

{adr_blocks}

# The change ({change.ref})

Commit message:
{change.message}

Changed lines (- removed, + added):
{chr(10).join(diff_lines)}

# Files after the change (for context; only the changed lines above may be cited)

{images or "(none available)"}
"""
    return ChatRequest(system=JUDGE_SYSTEM, user=user)
