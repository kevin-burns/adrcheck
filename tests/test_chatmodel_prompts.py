"""The judge prompt: what it asks for and in which order."""


def test_judge_schema_asks_for_the_reason_before_the_verdict():
    """A model that writes the label first and the reason second can talk itself out of the label while
    writing (GitLab MR !6, ADR-1/7: verdict CONFLICT, reason 'the finding is withdrawn'). Reason first, then
    the verdict that follows from it."""
    from adrcheck.chatmodel.prompts import JUDGE_SYSTEM

    schema = JUDGE_SYSTEM[JUDGE_SYSTEM.index('"findings"') :]
    assert schema.index('"reason"') < schema.index('"verdict"')
    assert "follows from the reason" in JUDGE_SYSTEM
