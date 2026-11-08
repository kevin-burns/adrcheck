"""Chat runner over the Anthropic Messages API. The SDK resolves its own access from the environment or an
`ant auth login` profile; this module reads nothing. The system text is one cached block, the user text follows."""

from __future__ import annotations

import time

from adrcheck.chatmodel import ChatReply, ChatRequest

# USD per million tokens: input, cache write, cache read, output. List prices, 2026-11; unknown model = 0.
_PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-opus-5-5": (4.0, 5.0, 0.20, 20.0),
    "claude-sonnet-5-5": (2.0, 2.5, 0.20, 10.0),
    "claude-haiku-5-5": (0.10, 0.125, 0.01, 0.50),
}


def estimate_cost(model: str, uncached: int, cache_write: int, cache_read: int, output: int) -> float:
    """List-price estimate. Zero for a model not in the table: a wrong number is worse than a missing one."""
    if model not in _PRICES:
        return 0.0
    p_in, p_write, p_read, p_out = _PRICES[model]
    return (uncached * p_in + cache_write * p_write + cache_read * p_read + output * p_out) / 1e6


class AnthropicRunner:
    def __init__(self, model: str = "claude-sonnet-5-5", client=None, max_tokens: int = 16000):
        if client is None:
            import anthropic  # local import keeps the SDK out of every path that does not call the API

            client = anthropic.Anthropic()
        self.model, self.client, self.max_tokens = model, client, max_tokens

    def run(self, request: ChatRequest) -> ChatReply:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": request.user}],
        }
        if request.system:
            kwargs["system"] = [{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}]
        started = time.monotonic()
        message = self.client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - started) * 1000)
        if getattr(message, "stop_reason", None) == "refusal":
            raise RuntimeError("model refused the request")
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        u = message.usage
        uncached = int(getattr(u, "input_tokens", 0) or 0)
        cache_write = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
        cache_read = int(getattr(u, "cache_read_input_tokens", 0) or 0)
        output = int(getattr(u, "output_tokens", 0) or 0)
        return ChatReply(
            text=text,
            tokens_in=uncached + cache_write + cache_read,
            tokens_out=output,
            cost_usd=estimate_cost(self.model, uncached, cache_write, cache_read, output),
            latency_ms=latency_ms,
        )
