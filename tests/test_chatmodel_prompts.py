"""The judge prompt: what it asks for and in which order."""


def test_judge_prompt_says_the_verdict_and_the_reason_must_agree():
    """GitLab MR !6, ADR-1/7: verdict CONFLICT, reason 'the finding is withdrawn'. Asking for the reason first
    cost recall on the planted corpora (PR #13, two runs), so the field order stays and the rule is said in
    words instead."""
    from adrcheck.chatmodel.prompts import JUDGE_SYSTEM

    assert "The verdict and the reason agree" in JUDGE_SYSTEM
    assert "Never a verdict\nthe reason withdraws" in JUDGE_SYSTEM
