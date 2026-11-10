"""Reports as JSON (one record per finding, the spike's row shape) and as markdown."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import groupby

from adrcheck.domain.verdict import Verdict
from adrcheck.usecases.check import ChangeReport

_SEVERITY = {Verdict.CONFLICT: 0, Verdict.UNCLEAR: 1, Verdict.ADR_OVERTAKEN: 2, Verdict.COMPLIANT: 3}
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
                    "adr_blob": f.adr_blob,
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


def _finding_lines(f, *, indent: str, label: str, with_id: bool) -> list[str]:
    head = f"{indent}- **{f.verdict.value}** {label}" + (f" ({f.obligation_id})" if with_id and f.obligation_id else "")
    if f.note:
        head += f" — {_prose(f.note)}"
    lines = [head]
    if f.line_text:
        lines.append(f"{indent}  - `{_code(f.path)}`: `{_code(f.line_text)}`")
    if f.quote:
        lines.append(f"{indent}  - > {_prose(f.quote)}")
    if f.reason:
        lines.append(f"{indent}  - {_prose(f.reason)}")
    return lines


_CQ_SEVERITY = {Verdict.CONFLICT: "major", Verdict.UNCLEAR: "minor", Verdict.ADR_OVERTAKEN: "info"}


def to_codequality(reports: list[ChangeReport]) -> str:
    """GitLab Code Quality (Code Climate) JSON: the merge-request widget reads it as an artifact, no token and no
    API call. One issue per finding that is not COMPLIANT; the fingerprint is stable across runs so GitLab can
    tell a new issue from one it has shown before."""
    issues = []
    for r in reports:
        for f in r.findings:
            if f.verdict not in _CQ_SEVERITY:
                continue
            quote = f" Decision: {f.quote}" if f.quote else ""
            reason = f" {f.reason}" if f.reason else ""
            note = f" ({f.note})" if f.note else ""
            key = "|".join([str(f.adr_number), f.obligation_id or "", f.path or "", f.line_text or ""])
            issues.append(
                {
                    "type": "issue",
                    "check_name": f"adrcheck/ADR-{f.adr_number}",
                    "description": f"{f.verdict.value} ADR-{f.adr_number}{note}.{quote}{reason}".strip(),
                    "categories": ["Style"],
                    "severity": _CQ_SEVERITY[f.verdict],
                    "fingerprint": hashlib.sha256(key.encode("utf-8")).hexdigest(),
                    "location": {"path": f.path or "", "lines": {"begin": f.line_number or 1}},
                }
            )
    return json.dumps(issues, indent=1)


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
        bare = sorted(
            {
                f.adr_number
                for f in r.findings
                if f.verdict is Verdict.COMPLIANT
                and not (f.obligation_id or f.line_text or f.quote or f.reason or f.note)
            }
        )
        cited = [f for f in r.findings if f.adr_number not in bare]
        ordered = sorted(cited, key=lambda f: (f.adr_number, _SEVERITY.get(f.verdict, 9), f.obligation_id or ""))
        for adr_number, group_iter in groupby(ordered, key=lambda f: f.adr_number):
            group = list(group_iter)
            if len(group) == 1:
                out.extend(_finding_lines(group[0], indent="", label=f"ADR-{adr_number}", with_id=True))
                continue
            # rnr: one head per (commit, ADR) with the worst verdict and the tally; the obligations sit beneath it
            tally = Counter(f.verdict.value for f in group)
            counts = ", ".join(
                f"{n} {v}" for v, n in sorted(tally.items(), key=lambda kv: _SEVERITY.get(Verdict(kv[0]), 9))
            )
            out.append(f"- **{group[0].verdict.value}** ADR-{adr_number} ({len(group)} obligations: {counts})")
            for f in group:
                out.extend(_finding_lines(f, indent="  ", label=f.obligation_id or f"ADR-{adr_number}", with_id=False))
        if bare:
            out.append("- compliant, nothing to cite: " + ", ".join(f"ADR-{n}" for n in bare))
        if dismissed:
            out.append("- judged, not relevant: " + ", ".join(f"ADR-{n}" for n in dismissed))
        if unjudged := [e.adr_number for e in r.excluded if e.reason.startswith("free tier:")]:
            out.append("- not judged, free tier: " + ", ".join(f"ADR-{n}" for n in unjudged))
        if cold := [e.adr_number for e in r.excluded if e.reason == "not compiled"]:
            out.append("- not compiled, run adrcheck compile: " + ", ".join(f"ADR-{n}" for n in cold))
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
