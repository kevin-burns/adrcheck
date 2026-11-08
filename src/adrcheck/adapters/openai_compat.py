"""Chat runner over the OpenAI-compatible `chat/completions` shape, which OpenAI, Ollama, vLLM, LM Studio and
OpenRouter all serve. No SDK: one JSON POST over urllib. The runner reads no environment; the composition root
hands it the base URL and the key. Cost is always 0: there is no price table a runner could trust for every
endpoint that speaks this protocol, and a wrong number is worse than a missing one (ADR-9, bead oao)."""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable
from urllib.parse import urlsplit

from adrcheck.chatmodel import ChatReply, ChatRequest

Post = Callable[[str, dict[str, str], bytes], dict]


def _post_json(url: str, headers: dict[str, str], body: bytes, timeout: float = 600.0) -> dict:
    if urlsplit(url).scheme not in ("http", "https"):
        raise ValueError(f"base_url must be http(s): {url!r}")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")  # noqa: S310
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  # nosec B310
        return json.loads(resp.read().decode("utf-8"))


class OpenAICompatRunner:
    def __init__(self, model: str, base_url: str, api_key: str = "", post: Post | None = None):
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key
        self.post = post or _post_json

    def run(self, request: ChatRequest) -> ChatReply:
        messages = [{"role": "user", "content": request.user}]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        started = time.monotonic()
        data = self.post(f"{self.base_url}/chat/completions", headers, body)
        latency_ms = int((time.monotonic() - started) * 1000)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"no choices in reply from {self.base_url}")
        first = choices[0]
        if first.get("finish_reason") == "content_filter":
            raise RuntimeError("content_filter: the endpoint withheld the reply")
        usage = data.get("usage") or {}
        return ChatReply(
            text=str((first.get("message") or {}).get("content") or ""),
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
            cost_usd=0.0,
            latency_ms=latency_ms,
        )
