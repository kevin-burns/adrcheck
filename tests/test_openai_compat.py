"""The OpenAI-compatible runner: one POST to chat/completions, faked at the transport, never the network."""

import json

import pytest

from adrcheck.adapters.openai_compat import OpenAICompatRunner
from adrcheck.adapters.providers import runner_for
from adrcheck.chatmodel import ChatRequest

REQ = ChatRequest(system="be brief", user="hello")


class FakePost:
    def __init__(self, reply=None):
        self.calls = []
        self.reply = reply or {
            "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 7},
        }

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, json.loads(body)))
        return self.reply


def test_the_runner_posts_system_and_user_messages_and_maps_the_reply():
    post = FakePost()
    runner = OpenAICompatRunner(model="qwen3:8b", base_url="http://ollama.example.invalid:11434/v1/", post=post)
    reply = runner.run(REQ)
    url, headers, body = post.calls[0]
    assert url == "http://ollama.example.invalid:11434/v1/chat/completions"
    assert "Authorization" not in headers and headers["Content-Type"] == "application/json"
    assert body["model"] == "qwen3:8b" and body["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hello"},
    ]
    assert (reply.text, reply.tokens_in, reply.tokens_out, reply.cost_usd) == ('{"ok": true}', 120, 7, 0.0)


def test_a_key_becomes_a_bearer_header_and_an_empty_system_sends_no_system_message():
    post = FakePost()
    OpenAICompatRunner(model="gpt-x", base_url="https://api.example/v1", api_key="k", post=post).run(
        ChatRequest(system="", user="hi")
    )
    _, headers, body = post.calls[0]
    assert headers["Authorization"] == "Bearer k" and [m["role"] for m in body["messages"]] == ["user"]


def test_a_content_filter_or_empty_choice_is_an_error_not_an_empty_verdict():
    filtered = FakePost({"choices": [{"message": {"content": ""}, "finish_reason": "content_filter"}], "usage": {}})
    with pytest.raises(RuntimeError, match="content_filter"):
        OpenAICompatRunner(model="m", base_url="http://h/v1", post=filtered).run(REQ)
    with pytest.raises(RuntimeError, match="no choices"):
        OpenAICompatRunner(model="m", base_url="http://h/v1", post=FakePost({"choices": []})).run(REQ)


def test_provider_specs_wire_openai_and_ollama_from_the_environment(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    r = runner_for("openai:gpt-x")
    assert (r.model, r.base_url, r.api_key) == ("gpt-x", "https://api.openai.com/v1", "")
    r = runner_for("ollama:qwen3:8b")  # the model name keeps its own colon
    assert (r.model, r.base_url, r.api_key) == ("qwen3:8b", "http://localhost:11434/v1", "")

    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.example/api/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.example.invalid:11434")
    r = runner_for("openai:some/model")
    assert (r.base_url, r.api_key) == ("https://openrouter.example/api/v1", "sk-test")
    assert runner_for("ollama:tev1").base_url == "http://ollama.example.invalid:11434/v1"


def test_an_http_error_surfaces_the_endpoints_own_message_not_a_traceback(monkeypatch):
    import io
    import urllib.error
    import urllib.request

    from adrcheck.adapters.openai_compat import _post_json

    body = b'{"error":{"message":"model requires 17.5 GiB but only 17.3 GiB are available","type":"api_error"}}'

    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, io.BytesIO(body))

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match=r"HTTP 500 from http://h/v1/chat/completions: model requires 17.5 GiB"):
        _post_json("http://h/v1/chat/completions", {}, b"{}")
