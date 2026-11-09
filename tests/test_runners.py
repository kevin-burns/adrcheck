"""Provider runners: each turns one ChatRequest into one ChatReply. Faked at the client, never the network."""

from types import SimpleNamespace

import pytest

from adrcheck.adapters.anthropic_api import AnthropicRunner, estimate_cost
from adrcheck.adapters.claude_cli import ClaudeCliRunner
from adrcheck.adapters.codex_cli import CodexCliRunner
from adrcheck.adapters.providers import runner_for
from adrcheck.chatmodel import ChatRequest

REQ = ChatRequest(system="be brief", user="hello")


def test_claude_cli_runner_maps_the_json_envelope_and_sends_system_plus_user_as_one_prompt():
    seen = {}

    def fake_run(prompt, model):
        seen["prompt"], seen["model"] = prompt, model
        return {
            "result": '{"ok": true}',
            "usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": 5,
                "cache_creation_input_tokens": 1,
                "output_tokens": 3,
            },
            "total_cost_usd": 0.02,
            "duration_api_ms": 300,
        }

    reply = ClaudeCliRunner(model="sonnet", run=fake_run).run(REQ)
    assert seen["model"] == "sonnet" and seen["prompt"].startswith("be brief") and seen["prompt"].endswith("hello")
    assert (reply.text, reply.tokens_in, reply.tokens_out, reply.cost_usd, reply.latency_ms) == (
        '{"ok": true}',
        16,
        3,
        0.02,
        300,
    )


# codex exec --json as codex-cli 0.166.0 printed it on 2026-11-10: the answer is the last agent_message item, the
# usage sits on turn.completed, and there is no cost field anywhere
CODEX_JSONL = "\n".join(
    [
        '{"type":"thread.started","thread_id":"01a1c2a3-4c4a-7e53-92cb-9298d0cb2640"}',
        '{"type":"item.completed","item":{"id":"item_0","type":"error","message":"Model metadata not found."}}',
        '{"type":"turn.started"}',
        '{"type":"item.completed","item":{"id":"item_1","type":"reasoning","text":"They want JSON."}}',
        '{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"{\\"ok\\": true}"}}',
        '{"type":"turn.completed","usage":{"input_tokens":4966,"cached_input_tokens":100,'
        '"cache_write_input_tokens":20,"output_tokens":73,"reasoning_output_tokens":0}}',
        "",
    ]
)


def test_codex_cli_runner_takes_the_last_agent_message_and_the_turn_usage_and_reports_no_cost():
    seen = {}

    def fake_run(prompt, model):
        seen["prompt"], seen["model"] = prompt, model
        return CODEX_JSONL

    reply = CodexCliRunner(model="gpt-5.5", run=fake_run).run(REQ)
    assert seen["model"] == "gpt-5.5" and seen["prompt"].startswith("be brief") and seen["prompt"].endswith("hello")
    assert (reply.text, reply.tokens_in, reply.tokens_out, reply.cost_usd) == ('{"ok": true}', 5086, 73, 0.0)
    assert reply.latency_ms >= 0


def test_codex_cli_runner_raises_on_a_failed_turn_or_a_turn_with_no_message():
    failed = (
        '{"type":"turn.started"}\n{"type":"turn.failed","error":{"message":"unexpected status 401 Unauthorized"}}\n'
    )
    with pytest.raises(RuntimeError, match="401 Unauthorized"):
        CodexCliRunner(model="gpt-5.5", run=lambda p, m: failed).run(REQ)
    with pytest.raises(RuntimeError, match="no agent_message"):
        CodexCliRunner(model="gpt-5.5", run=lambda p, m: '{"type":"turn.completed","usage":{}}\n').run(REQ)


def test_codex_cli_spec_picks_the_runner_and_an_empty_model_leaves_the_choice_to_codex():
    assert (
        isinstance(runner_for("codex-cli:gpt-5.5"), CodexCliRunner)
        and runner_for("codex-cli:gpt-5.5").model == "gpt-5.5"
    )
    assert runner_for("codex-cli:").model == ""


class FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"ok": true}')],
            stop_reason="end_turn",
            usage=SimpleNamespace(
                input_tokens=1000, cache_creation_input_tokens=2000, cache_read_input_tokens=3000, output_tokens=100
            ),
        )


def test_anthropic_runner_caches_the_system_block_and_prices_the_usage():
    messages = FakeMessages()
    client = SimpleNamespace(messages=messages)
    reply = AnthropicRunner(model="claude-sonnet-5-5", client=client).run(REQ)
    [call] = messages.calls
    assert call["model"] == "claude-sonnet-5-5"
    assert call["system"] == [{"type": "text", "text": "be brief", "cache_control": {"type": "ephemeral"}}]
    assert call["messages"] == [{"role": "user", "content": "hello"}]
    assert reply.text == '{"ok": true}' and (reply.tokens_in, reply.tokens_out) == (6000, 100)
    # Sonnet 5.5 list price: $2 input, $2.50 cache write, $0.20 cache read, $10 output per million
    assert reply.cost_usd == pytest.approx(0.001 * 2 + 0.002 * 2.5 + 0.003 * 0.2 + 0.0001 * 10)


def test_anthropic_runner_sends_no_system_block_when_the_request_has_none():
    messages = FakeMessages()
    AnthropicRunner(model="claude-sonnet-5-5", client=SimpleNamespace(messages=messages)).run(
        ChatRequest(system="", user="x")
    )
    assert "system" not in messages.calls[0]


def test_unknown_model_is_priced_at_zero_and_flagged_rather_than_guessed():
    assert estimate_cost("some-future-model", 1, 1, 1, 1) == 0.0


def test_provider_strings_pick_a_runner_and_a_bare_name_means_the_claude_cli():
    assert runner_for("claude-cli:sonnet").model == "sonnet"
    assert runner_for("sonnet").model == "sonnet"
    assert (
        type(runner_for("anthropic:claude-sonnet-5-5", client=SimpleNamespace(messages=None))).__name__
        == "AnthropicRunner"
    )
    with pytest.raises(ValueError):
        runner_for("nope:thing")
