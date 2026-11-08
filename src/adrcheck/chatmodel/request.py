"""What a chat provider is asked and what it answers. One request, one reply, no conversation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatRequest:
    system: str  # stable instructions; a provider may cache them. Empty means none.
    user: str


@dataclass(frozen=True)
class ChatReply:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class ChatRunner(Protocol):
    model: str

    def run(self, request: ChatRequest) -> ChatReply: ...
