"""A judge call can take ten seconds or more. At a terminal, say so before it starts and when it ends."""

import io

from adrcheck.adapters.progress import Announcing
from adrcheck.domain.change import Change
from adrcheck.ports import JudgeResponse


class Slow:
    def judge(self, change, cases, context):
        return JudgeResponse(findings=())


def test_announcing_judge_says_what_it_is_judging_and_how_long_it_took():
    out = io.StringIO()
    judge = Announcing(Slow(), model="openai:gpt-6-luna", out=out)
    response = judge.judge(Change(ref="36f6b01e32", message="m"), cases=((1, "x"), (3, "y")), context=None)
    assert response.findings == ()
    lines = out.getvalue().splitlines()
    assert lines[0] == "judging 36f6b01 (2 ADRs) with openai:gpt-6-luna ..."
    assert lines[1].startswith("judged 36f6b01 in ") and lines[1].endswith(" s")


def test_announcing_judge_is_quiet_when_given_no_stream():
    judge = Announcing(Slow(), model="m", out=None)
    judge.judge(Change(ref="abc1234", message="m"), cases=(), context=None)  # no error, nothing to assert
