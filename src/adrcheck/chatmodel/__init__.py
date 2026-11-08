"""A chat model fills two seats, compiler and judge, over any provider that can answer one ChatRequest.

Providers live in adapters (claude -p, the Anthropic SDK, later an OpenAI-compatible endpoint). This package
holds what they share: the prompts, the parsers and the seat logic. It imports no provider.
"""

from __future__ import annotations

from adrcheck.chatmodel.parse import parse_compile_reply, parse_judge_reply
from adrcheck.chatmodel.prompts import PROMPT_VERSION, compile_request, judge_request
from adrcheck.chatmodel.request import ChatReply, ChatRequest, ChatRunner
from adrcheck.domain.adr import Adr
from adrcheck.domain.change import Change
from adrcheck.domain.obligation import Obligation
from adrcheck.ports import Context, JudgeCase, JudgeResponse

__all__ = ["PROMPT_VERSION", "ChatModelSeats", "ChatReply", "ChatRequest", "ChatRunner"]


class ChatModelSeats:
    """Implements both ObligationCompiler and ChangeJudge; one chat runner, two roles."""

    def __init__(self, run: ChatRunner):
        self.runner = run
        self.last_usage: dict = {}

    def compile(self, adr: Adr) -> tuple[Obligation, ...]:
        reply = self.runner.run(compile_request(adr))
        self.last_usage = {"tokens_in": reply.tokens_in, "tokens_out": reply.tokens_out, "cost_usd": reply.cost_usd}
        return parse_compile_reply(reply.text, adr)

    def judge(self, change: Change, cases: tuple[JudgeCase, ...], context: Context) -> JudgeResponse:
        try:
            reply = self.runner.run(judge_request(change, cases, context))
        except Exception as exc:
            return JudgeResponse(error=f"{type(exc).__name__}: {exc}"[:300])
        parsed = parse_judge_reply(reply.text)
        return JudgeResponse(
            findings=parsed.findings,
            not_relevant=parsed.not_relevant,
            error=parsed.error,
            tokens_in=reply.tokens_in,
            tokens_out=reply.tokens_out,
            cost_usd=reply.cost_usd,
            latency_ms=reply.latency_ms,
        )
