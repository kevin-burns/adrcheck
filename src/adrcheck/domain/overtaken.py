"""Q14: a contradiction already present at the parent commit was not introduced by this one.

The judge sees only the diff. Two cheap probes of the parent snapshot settle who moved first:
whether what the ADR mandates still existed, and whether what it forbids was already there.
`None` means the probe was unavailable; then the judge's verdict stands.
"""

from __future__ import annotations

from adrcheck.domain.verdict import Verdict


def classify(judge: Verdict, *, mandated_at_parent: bool | None, forbidden_at_parent: bool | None) -> Verdict:
    if mandated_at_parent is False:
        return Verdict.ADR_OVERTAKEN
    if judge is Verdict.CONFLICT and forbidden_at_parent is True:
        return Verdict.ADR_OVERTAKEN
    return judge
