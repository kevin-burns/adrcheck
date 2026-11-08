"""`provider:model` strings to runners. The composition root's one lookup table for chat providers."""

from __future__ import annotations

from adrcheck.adapters.anthropic_api import AnthropicRunner
from adrcheck.adapters.claude_cli import ClaudeCliRunner
from adrcheck.chatmodel import ChatRunner

PROVIDERS = ("claude-cli", "anthropic")


def runner_for(spec: str, **kwargs) -> ChatRunner:
    """'anthropic:claude-sonnet-5-5', 'claude-cli:sonnet', or a bare model name, which means the claude CLI."""
    provider, sep, model = spec.partition(":")
    if not sep:
        provider, model = "claude-cli", spec
    if provider == "claude-cli":
        return ClaudeCliRunner(model=model or "sonnet")
    if provider == "anthropic":
        return AnthropicRunner(model=model or "claude-sonnet-5-5", **kwargs)
    raise ValueError(f"unknown provider {provider!r}; one of {', '.join(PROVIDERS)}")
