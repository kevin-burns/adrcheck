"""Q14: a contradiction already present at the parent commit was not introduced by this one."""

import pytest

from adrcheck.domain.overtaken import classify
from adrcheck.domain.verdict import Verdict


@pytest.mark.parametrize(
    "judge, mandated_at_parent, forbidden_at_parent, expected",
    [
        (Verdict.CONFLICT, True, False, Verdict.CONFLICT),  # commit removed or broke what the ADR mandates
        (Verdict.CONFLICT, False, False, Verdict.ADR_OVERTAKEN),  # the mandated thing was already gone
        (Verdict.CONFLICT, True, True, Verdict.ADR_OVERTAKEN),  # the forbidden pattern already existed elsewhere
        (Verdict.CONFLICT, None, None, Verdict.CONFLICT),  # no probe available: trust the judge
        (Verdict.COMPLIANT, True, False, Verdict.COMPLIANT),
        (Verdict.COMPLIANT, False, False, Verdict.COMPLIANT),  # see the test below: the change may be what adds it
        (Verdict.UNCLEAR, False, False, Verdict.UNCLEAR),
        (Verdict.UNCLEAR, True, False, Verdict.UNCLEAR),
    ],
)
def test_classification_table(judge, mandated_at_parent, forbidden_at_parent, expected):
    assert classify(judge, mandated_at_parent=mandated_at_parent, forbidden_at_parent=forbidden_at_parent) is expected


def test_a_conflict_over_a_removed_anchor_that_nothing_used_at_parent_is_overtaken():
    assert classify(Verdict.CONFLICT, mandated_at_parent=True, forbidden_at_parent=False, dead_at_parent=True) is (
        Verdict.ADR_OVERTAKEN
    )
    assert classify(Verdict.CONFLICT, mandated_at_parent=True, forbidden_at_parent=False, dead_at_parent=False) is (
        Verdict.CONFLICT
    )
    # the probe is only about conflicts; a compliant verdict never flips on it
    assert classify(Verdict.COMPLIANT, mandated_at_parent=True, forbidden_at_parent=False, dead_at_parent=True) is (
        Verdict.COMPLIANT
    )


def test_a_compliant_change_that_introduces_the_mandated_anchor_stays_compliant():
    """ADR-7 flips a CONFLICT whose contradiction can be shown at the parent. It says nothing about COMPLIANT.
    Seen on adrcheck's own 8dfe76d: the ADR names `occurrences()`, this commit is the one that added it, so
    the anchor was absent at the parent; the judge said COMPLIANT and the old rule overrode it with a
    'contradiction already present at parent' that did not exist. An anchor missing at both ends of the
    range is the stale sweep's business (ADR-5), not a per-finding verdict."""
    assert classify(Verdict.COMPLIANT, mandated_at_parent=False, forbidden_at_parent=False) is Verdict.COMPLIANT
    assert classify(Verdict.UNCLEAR, mandated_at_parent=False, forbidden_at_parent=None) is Verdict.UNCLEAR
    assert classify(Verdict.CONFLICT, mandated_at_parent=False, forbidden_at_parent=False) is Verdict.ADR_OVERTAKEN
