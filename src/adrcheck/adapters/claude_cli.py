"""Chat runner over `claude -p`: works wherever Claude Code is installed and logged in."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - argv-list calls only, see run_claude
import tempfile
from collections.abc import Callable

from adrcheck.chatmodel import ChatReply, ChatRequest

Runner = Callable[[str, str], dict]


def run_claude(prompt: str, model: str) -> dict:
    proc = subprocess.run(  # nosec B603 B607 - argv list, no shell; claude resolved from PATH by design
        ["claude", "-p", "--output-format", "json", "--model", model, "--tools", ""],
        input=prompt,
        capture_output=True,
        text=True,
        check=True,
        cwd=tempfile.gettempdir(),  # a neutral cwd: no project CLAUDE.md or MCP servers join the prompt
    )
    return json.loads(proc.stdout)


class ClaudeCliRunner:
    def __init__(self, model: str = "sonnet", run: Runner = run_claude):
        self.model, self._run = model, run

    def run(self, request: ChatRequest) -> ChatReply:
        prompt = f"{request.system}\n\n{request.user}" if request.system else request.user
        raw = self._run(prompt, self.model)
        u = raw.get("usage", {}) or {}
        return ChatReply(
            text=str(raw.get("result", "")),
            tokens_in=int(u.get("input_tokens", 0))
            + int(u.get("cache_read_input_tokens", 0))
            + int(u.get("cache_creation_input_tokens", 0)),
            tokens_out=int(u.get("output_tokens", 0)),
            cost_usd=float(raw.get("total_cost_usd", 0.0)),
            latency_ms=int(raw.get("duration_api_ms", 0)),
        )
