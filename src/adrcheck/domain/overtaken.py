"""Q14: a contradiction already present at the parent commit was not introduced by this one.

The judge sees only the diff. Two cheap probes of the parent snapshot settle who moved first:
whether what the ADR mandates still existed, and whether what it forbids was already there.
`None` means the probe was unavailable; then the judge's verdict stands.
"""

from __future__ import annotations

from adrcheck.domain.verdict import Verdict


def classify(
    judge: Verdict,
    *,
    mandated_at_parent: bool | None,
    forbidden_at_parent: bool | None,
    dead_at_parent: bool | None = None,
) -> Verdict:
    """`dead_at_parent`: the conflict cites the removal of an anchor nothing else referenced at the parent.
    Deleting dead code does not break a decision; the decision had already been left behind (bead ihg)."""
    if judge is Verdict.COMPLIANT:
        # A COMPLIANT change whose mandated anchor is absent at the parent may be the very change that adds it;
        # an anchor gone at both ends is the stale sweep's finding (ADR-5). Nothing here overrides a pass.
        return judge
    if dead_at_parent is True:
        # Deleting a name nothing referenced is dead code whether the judge called it a conflict or could not
        # tell. The judge sees the diff; the count sees the parent (ADR-7, third probe).
        return Verdict.ADR_OVERTAKEN
    if judge is Verdict.CONFLICT and (mandated_at_parent is False or forbidden_at_parent is True):
        return Verdict.ADR_OVERTAKEN
    return judge
