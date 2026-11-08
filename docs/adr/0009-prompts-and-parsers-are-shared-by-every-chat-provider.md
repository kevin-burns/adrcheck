# 9. Prompts and parsers are policy shared by every chat provider; a provider is only a runner

Date: 2026-11-08
Status: Accepted
Bead: adrcheck-oao
Applies to: src/adrcheck/chatmodel/**, src/adrcheck/adapters/claude_cli.py, src/adrcheck/adapters/anthropic_api.py, src/adrcheck/adapters/providers.py

## Context

The first adapter owned everything: the prompt text, the reply parsers and the `claude -p` subprocess.
adrcheck must run where there is no Claude Code, in CI with an API key, and later against OpenAI-compatible
endpoints. If each provider carried its own prompt, the eval set would compare prompt variants instead of
models, and a fix to one parser would not reach the others.

## Decision

The package `src/adrcheck/chatmodel/` holds the prompt text (`prompts.py`, including `PROMPT_VERSION`), the
reply parsers (`parse.py`) and `ChatModelSeats`, which implements both `ObligationCompiler` and
`ChangeJudge` over one `ChatRunner`. A `ChatRunner` turns one `ChatRequest` (system text plus user text)
into one `ChatReply` (text and usage). Providers are runners in `src/adrcheck/adapters/`: `ClaudeCliRunner`
over `claude -p` and `AnthropicRunner` over the Anthropic Messages API, selected by a `provider:model`
string in `providers.py`. `chatmodel` imports no adapter, no SDK and no subprocess. A runner that raises
makes the judge return an error response; it never raises through the use case.

## Consequences

Every provider sends the same words, so the eval set compares models. The compile prompt stays
byte-identical to the first adapter's, so cached obligations under the current `PROMPT_VERSION` remain
valid. Adding a provider is one runner file and one line in `providers.py`. The system text of the judge
request is a cacheable block for providers that cache; `claude -p` concatenates it, which is the same
prompt in one piece. Cost for the Anthropic runner is a list-price estimate from a table and is zero for an
unknown model, which is reported as such rather than guessed.
