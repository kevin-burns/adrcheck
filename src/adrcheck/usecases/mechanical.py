"""The free tier's judge: deterministic, no model, no key (bead 2wa).

A use case, not domain: it implements the ChangeJudge port and builds the port's own types, and ADR-1 keeps
the domain free of ports; adrcheck's own self-check flagged the first draft of this file for living under
domain/ (PR #2). An obligation's forbidden patterns found on an added line are a CONFLICT claim carrying the
obligation's own quote. The claim then goes through the same verify() and parent probes as a model's, so a
mechanical CONFLICT is held to the same evidence rule. Mandates cannot be judged this way: an absence is not
visible in a diff. Those ADRs are reported as not judged, never as compliant."""

from __future__ import annotations

from adrcheck.domain.change import Change
from adrcheck.domain.verdict import Verdict
from adrcheck.ports import Context, JudgeCase, JudgeResponse, RawFinding


class MechanicalJudge:
    def judge(self, change: Change, cases: tuple[JudgeCase, ...], context: Context) -> JudgeResponse:
        findings: list[RawFinding] = []
        for case in cases:
            for o in case.obligations:
                if not o.forbids:
                    continue
                for f in change.files:
                    for line in f.added:
                        hit = next((p for p in o.forbids if p in line.text), None)
                        if hit is None:
                            continue
                        findings.append(
                            RawFinding(
                                obligation_id=o.id,
                                verdict=Verdict.CONFLICT,
                                path=f.path,
                                line_text=line.text,
                                quote=o.quote,
                                reason=f"added line contains the forbidden pattern {hit!r}",
                            )
                        )
        return JudgeResponse(findings=tuple(findings))
