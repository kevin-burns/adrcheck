"""A judge that says what it is doing. A judge call takes seconds to tens of seconds and prints nothing while
it waits; at a terminal that looks like a hang. This wrapper writes one line before the call and one after,
to the stream it is given, and nothing when given none, which is what CI gets. Attribute reads fall through
to the wrapped judge, so `last_usage` and friends still work."""

from __future__ import annotations

import time
from typing import IO

from adrcheck.domain.change import Change
from adrcheck.ports import ChangeJudge, Context, JudgeCase, JudgeResponse


class Announcing:
    def __init__(self, judge: ChangeJudge, model: str, out: IO[str] | None):
        self._judge, self._model, self._out = judge, model, out

    def judge(self, change: Change, cases: tuple[JudgeCase, ...], context: Context) -> JudgeResponse:
        short = change.ref[:7]
        if self._out:
            n = len(cases)
            print(
                f"judging {short} ({n} ADR{'' if n == 1 else 's'}) with {self._model} ...", file=self._out, flush=True
            )
        started = time.monotonic()
        try:
            return self._judge.judge(change, cases, context)
        finally:
            if self._out:
                print(f"judged {short} in {time.monotonic() - started:.1f} s", file=self._out, flush=True)

    def __getattr__(self, name: str):
        return getattr(self._judge, name)
