"""Q14: a contradiction already present at the parent commit was not introduced by this one."""

import pytest

from adrcheck.domain.verdict import Verdict
from adrcheck.domain.overtaken import classify


@pytest.mark.parametrize(
    "judge, mandated_at_parent, forbidden_at_parent, expected",
    [
        (Verdict.CONFLICT, True, False, Verdict.CONFLICT),          # commit removed or broke what the ADR mandates
        (Verdict.CONFLICT, False, False, Verdict.ADR_OVERTAKEN),    # the mandated thing was already gone
        (Verdict.CONFLICT, True, True, Verdict.ADR_OVERTAKEN),      # the forbidden pattern already existed elsewhere
        (Verdict.CONFLICT, None, None, Verdict.CONFLICT),           # no probe available: trust the judge
        (Verdict.COMPLIANT, True, False, Verdict.COMPLIANT),
        (Verdict.COMPLIANT, False, False, Verdict.ADR_OVERTAKEN),   # compliant diff, but the ADR's subject no longer exists
        (Verdict.UNCLEAR, False, False, Verdict.ADR_OVERTAKEN),
        (Verdict.UNCLEAR, True, False, Verdict.UNCLEAR),
    ],
)
def test_classification_table(judge, mandated_at_parent, forbidden_at_parent, expected):
    assert classify(judge, mandated_at_parent=mandated_at_parent, forbidden_at_parent=forbidden_at_parent) is expected
