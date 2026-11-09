# 14. The openai: and ollama: runners report zero cost on purpose

Date: 2026-11-10
Status: Accepted
Applies to: src/adrcheck/adapters/openai_compat.py, src/adrcheck/adapters/providers.py

## Context

The `openai:` and `ollama:` providers both run on `OpenAICompatRunner`, which talks to any endpoint that
speaks the `chat/completions` protocol. No price table fits every endpoint that speaks this protocol, so
any built-in price would be wrong for some of them, and a wrong number is worse than a missing one. Users
who rely on the cost field in the JSON report would be misled by a wrong figure, and once they rely on it
the meaning of the field is hard to change back.

## Decision

`OpenAICompatRunner.run` in `src/adrcheck/adapters/openai_compat.py` always returns a `ChatReply` with
`cost_usd` of 0.0, whatever the model or endpoint. It never computes a price from a model name or a built-in
table.

`runner_for` in `src/adrcheck/adapters/providers.py` builds `OpenAICompatRunner` for both the `openai:` and
the `ollama:` prefix, so both report zero cost. No price table is added to either file.

The runner does report `tokens_in` and `tokens_out`. The cost is worked out from those token counts in the
JSON report and the provider's own price list, outside adrcheck.

## Consequences

For these two providers a `cost_usd` of 0 means "not reported", not "free". This surprises people who
expect a cost, so `docs/providers.md` states it. Reporting a real figure from these runners would change
what the field means for users who rely on it, so it needs a new record that supersedes this one.

## Considered options

- A built-in price table: rejected. No price table fits every endpoint that speaks this protocol, and a
  wrong number is worse than a missing one.
- Report zero cost and leave the calculation to the user: chosen.
