"""`provider:model` strings to runners. The composition root's one lookup table for chat providers, and the
only place a provider's environment (base URL, key) is read."""

from __future__ import annotations

import os

from adrcheck.adapters.anthropic_api import AnthropicRunner
from adrcheck.adapters.claude_cli import ClaudeCliRunner
from adrcheck.adapters.openai_compat import OpenAICompatRunner
from adrcheck.chatmodel import ChatRunner

PROVIDERS = ("claude-cli", "anthropic", "openai", "ollama")


def runner_for(spec: str, **kwargs) -> ChatRunner:
    """'anthropic:claude-sonnet-5-5', 'claude-cli:sonnet', 'openai:gpt-x', 'ollama:qwen3:8b', or a bare model
    name, which means the claude CLI. The model keeps everything after the first colon."""
    provider, sep, model = spec.partition(":")
    if not sep:
        provider, model = "claude-cli", spec
    if provider == "claude-cli":
        return ClaudeCliRunner(model=model or "sonnet")
    if provider == "anthropic":
        return AnthropicRunner(model=model or "claude-sonnet-5-5", **kwargs)
    if provider == "openai":
        base = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        return OpenAICompatRunner(model=model, base_url=base, api_key=os.environ.get("OPENAI_API_KEY", ""), **kwargs)
    if provider == "ollama":
        host = (os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        return OpenAICompatRunner(model=model, base_url=f"{host}/v1", **kwargs)
    raise ValueError(f"unknown provider {provider!r}; one of {', '.join(PROVIDERS)}")
