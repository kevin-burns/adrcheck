"""Chat runner over `codex exec`: works wherever the Codex CLI is installed and logged in, with or without
an API key. One prompt in on stdin, JSONL events out; the reply is the last `agent_message` item and the
usage sits on `turn.completed`. Codex reports no cost, so cost_usd is 0 (ADR-14's reasoning, same seat).

Event shape read from codex-cli 0.166.0 on 2026-11-10; the official page (learn.chatgpt.com, non-interactive
mode) shows the same `item.completed` / `agent_message` / `text` fields."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - argv-list calls only, see run_codex
import tempfile
import time
from collections.abc import Callable

from adrcheck.chatmodel import ChatReply, ChatRequest

Runner = Callable[[str, str], str]


def run_codex(prompt: str, model: str) -> str:
    """One non-interactive turn: read-only sandbox, nothing persisted, a neutral cwd so no project AGENTS.md
    joins the prompt. An empty model leaves the choice to the Codex config."""
    argv = ["codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "--color", "never"]
    if model:
        argv += ["-m", model]
    proc = subprocess.run(  # nosec B603 B607 - argv list, no shell; codex resolved from PATH by design
        [*argv, "-"],
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
        cwd=tempfile.gettempdir(),
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(f"codex exec exited {proc.returncode}: {proc.stderr.strip()[-500:]}")
    return proc.stdout


class CodexCliRunner:
    def __init__(self, model: str = "", run: Runner = run_codex):
        self.model, self._run = model, run

    def run(self, request: ChatRequest) -> ChatReply:
        prompt = f"{request.system}\n\n{request.user}" if request.system else request.user
        started = time.perf_counter()
        events = _events(self._run(prompt, self.model))
        latency_ms = int((time.perf_counter() - started) * 1000)
        text, usage = None, {}
        for ev in events:
            kind = ev.get("type")
            if kind == "turn.failed":
                raise RuntimeError(f"codex turn failed: {(ev.get('error') or {}).get('message', '')}")
            if kind == "item.completed" and (ev.get("item") or {}).get("type") == "agent_message":
                text = str(ev["item"].get("text", ""))
            if kind == "turn.completed":
                usage = ev.get("usage") or {}
        if text is None:
            raise RuntimeError("codex exec produced no agent_message")
        return ChatReply(
            text=text,
            tokens_in=int(usage.get("input_tokens", 0))
            + int(usage.get("cached_input_tokens", 0))
            + int(usage.get("cache_write_input_tokens", 0)),
            tokens_out=int(usage.get("output_tokens", 0)),
            cost_usd=0.0,
            latency_ms=latency_ms,
        )


def _events(jsonl: str) -> list[dict]:
    out = []
    for line in jsonl.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
