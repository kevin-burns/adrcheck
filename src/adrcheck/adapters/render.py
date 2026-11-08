"""Reports as JSON (one record per finding, the spike's row shape) and as markdown."""

from __future__ import annotations

import json

from adrcheck.usecases.check import ChangeReport

TEXT_LIMIT = 300  # judge text, cited lines and quotes are untrusted input to a PR comment


def _prose(text: str) -> str:
    """One line, no HTML, bounded: model text cannot open a heading, hide a comment or fill the page."""
    flat = " ".join(text.split()).replace("<", "&lt;")
    return flat if len(flat) <= TEXT_LIMIT else flat[:TEXT_LIMIT] + "…"


def _code(text: str) -> str:
    """Fit for one backtick span: a backtick inside would end it early."""
    flat = " ".join(text.split()).replace("`", "'")
    return flat if len(flat) <= TEXT_LIMIT else flat[:TEXT_LIMIT] + "…"


def _finding_rows(reports: list[ChangeReport]) -> list[dict]:
    rows = []
    for r in reports:
        for f in r.findings:
            rows.append(
                {
                    "commit": r.ref,
                    "adr": f.adr_number,
                    "obligation": f.obligation_id,
                    "verdict": f.verdict.value,
                    "signals": sorted(f.signals),
                    "path": f.path,
                    "line_text": f.line_text,
                    "quote": f.quote,
                    "reason": f.reason,
                    "verify_failed": list(f.verify_failed),
                    "note": f.note,
                    "label": "",
                }
            )
    return rows


def to_json(reports: list[ChangeReport]) -> str:
    return json.dumps(
        {
            "changes": [
                {
                    "commit": r.ref,
                    "subject": r.message.splitlines()[0] if r.message else "",
                    "uncovered": r.uncovered,
                    "judge_calls": r.judge_calls,
                    "tokens_in": r.tokens_in,
                    "tokens_out": r.tokens_out,
                    "cost_usd": round(r.cost_usd, 4),
                    "excluded": [{"adr": e.adr_number, "reason": e.reason} for e in r.excluded],
                    "problems": list(r.problems),
                    "decision_signals": [
                        {"kind": s.kind, "detail": s.detail} for s in getattr(r, "decision_signals", ())
                    ],
                }
                for r in reports
            ],
            "findings": _finding_rows(reports),
            "stale": [
                {"adr": s.adr_number, "obligation": s.obligation_id, "missing": list(s.missing), "known": s.known}
                for r in reports
                for s in r.stale
            ],
        },
        indent=1,
    )


def to_markdown(reports: list[ChangeReport]) -> str:
    """Lint-clean markdown: a blank line after every heading and around every list, so it pastes into a PR."""
    out: list[str] = []
    for r in reports:
        subject = r.message.splitlines()[0] if r.message else ""
        out.append(f"## {r.ref[:10]} {subject}")
        out.append("")
        dismissed = [e.adr_number for e in r.excluded if e.reason.startswith("model:")]
        if not r.findings and not dismissed:
            out.append("_No ADR applied to this change._")
            out.append("")
        for f in r.findings:
            head = f"- **{f.verdict.value}** ADR-{f.adr_number}" + (f" ({f.obligation_id})" if f.obligation_id else "")
            if f.note:
                head += f" — {_prose(f.note)}"
            out.append(head)
            if f.line_text:
                out.append(f"  - `{_code(f.path)}`: `{_code(f.line_text)}`")
            if f.quote:
                out.append(f"  - > {_prose(f.quote)}")
            if f.reason:
                out.append(f"  - {_prose(f.reason)}")
        if dismissed:
            out.append("- judged, not relevant: " + ", ".join(f"ADR-{n}" for n in dismissed))
        if proposed := [e.adr_number for e in r.excluded if "touches its paths" in e.reason]:
            out.append("- proposed, not enforced, touches its paths: " + ", ".join(f"ADR-{n}" for n in proposed))
        if r.uncovered:
            out.append(f"- uncovered files: {r.uncovered}")
        for p in r.problems:
            out.append(f"- problem: {_prose(p)}")
        out.append("")
    stale = [s for r in reports for s in r.stale]
    if stale:
        out.append("## Possibly overtaken ADRs (named anchors missing at the end of the range)")
        out.append("")
        for s in stale:
            if not s.known:
                out.append(f"- ADR-{s.adr_number} {s.obligation_id}: missing {', '.join(repr(m) for m in s.missing)}")
        if known := sum(s.known for s in stale):
            out.append(f"- {known} already in the baseline")
        out.append("")
    return "\n".join(out)
