# Providers

adrcheck makes two kinds of model call. The compile seat turns one ADR into obligations, once, and the
result is cached under `.adrcheck/obligations/`. The judge seat reads one commit against every ADR that
governs a path it touches, one call per commit. The judge is where the money goes, so this page is mostly
about choosing a judge.

Both seats take a `provider:model` string. `--model` sets both. `--compile-model` moves the compile seat
somewhere else, for example a local model for the once-per-ADR compile and a hosted one for the judge.

## The four providers

| Prefix | What it talks to | Environment | Cost reported |
|---|---|---|---|
| `anthropic:` | Anthropic API through the SDK | `ANTHROPIC_API_KEY` | from the SDK's usage figures |
| `claude-cli:` | a logged-in Claude Code install (`claude -p`) | none | the CLI's own figure |
| `openai:` | any endpoint that serves `chat/completions` | `OPENAI_BASE_URL`, `OPENAI_API_KEY` | always 0 |
| `ollama:` | an Ollama server's OpenAI-compatible route | `OLLAMA_HOST` (default `http://localhost:11434`) | always 0 |

Default when `--model` is absent: `anthropic:claude-sonnet-5-5` if the Anthropic key variable is set,
else `claude-cli:sonnet`.

The `openai:` and `ollama:` runners report zero cost on purpose. No price table fits every endpoint that
speaks this protocol, and a wrong number is worse than a missing one. Work the cost out from the token
counts in the JSON report and the provider's own price list.

The model part keeps everything after the first colon, so `ollama:qwen3:8b` is model `qwen3:8b`.

### Anthropic API

```sh
export ANTHROPIC_API_KEY=...   # or `ant auth login`
adrcheck check --range origin/main..HEAD --model anthropic:claude-sonnet-5-5
```

### Claude Code CLI

Needs a Claude Code install that is already logged in. No key is read. Per-run dollar figures from this
route are noisy because the CLI's prompt cache state changes between runs; compare input tokens, not dollars,
when two runs need to be compared.

```sh
adrcheck check --range origin/main..HEAD --model claude-cli:sonnet
```

### OpenAI-compatible endpoints, including OpenRouter

Anything that serves `POST {base}/chat/completions` with the OpenAI message shape: OpenAI, OpenRouter,
vLLM, LM Studio. The runner sends a Bearer header only when a key is set.

```sh
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=...      # the OpenRouter key
adrcheck check --range origin/main..HEAD --model openai:anthropic/claude-haiku-5.5
```

With `OPENAI_BASE_URL` unset the runner talks to `https://api.openai.com/v1`.

An HTTP error surfaces the endpoint's own message, for example `HTTP 500 from ...: model requires 17.5 GiB
but only 17.3 GiB are available`, and `check` exits 3: could not evaluate, which is a warning and not a
finding.

### Ollama

```sh
export OLLAMA_HOST=http://<host>:11434   # omit for a local server
adrcheck check --range origin/main..HEAD --model ollama:qwen3.5:9b-q8_0
```

Measured on 2026-11-08 against a shared Apple-silicon host: a 9B model compiled one ADR into three
obligations in 4 min 14 s from a cold load. A 27B model did not fit beside the other work on the machine.
That speed fits the compile seat, which runs once per ADR and is cached. It does not fit a judge that CI
waits on. Details in [the Ollama spike](spikes/2026-11-08-ollama-runner.md).

## Mixing seats

```sh
adrcheck check --range origin/main..HEAD \
  --compile-model ollama:qwen3.5:9b-q8_0 \
  --model openai:anthropic/claude-haiku-5.5
```

The obligation cache is keyed by ADR text and prompt version, not by the model that compiled it. After
changing `--compile-model`, delete `.adrcheck/obligations/` to recompile. Whether the key should include
the model is an open decision.

## Choosing a judge: what has been measured

The frozen adrcheck corpus (`evals/cases/adrcheck.json`) is one commit and eleven labelled rows, all
COMPLIANT. Every judge below scored 11/11, and that is a weak result: a judge that stays silent on every
row also scores 11/11, because a quiet row counts as a hit when the label is COMPLIANT. The "asserted"
column is how many of the eleven rows the judge actually named as compliant. The compile seat was the
cached Sonnet output in every run, so the table compares judges only.

| Judge | Route | Asserted | Tokens in / out | Cost | Wall time |
|---|---|---|---|---|---|
| claude-sonnet-5-5 | claude-cli | 6 of 11 | 108,549 / 2,831 | $0.31 reported | not timed |
| anthropic/claude-haiku-5.5 | OpenRouter | 6 of 11 | 58,655 / 6,611 | about $0.01 | 28 s |
| deepseek/deepseek-v4-flash | OpenRouter | 3 of 11 | 40,898 / 26,916 | about $0.01 | 5 min 38 s |
| deepseek/deepseek-v4-pro | OpenRouter | 1 of 11 | 40,819 / 7,446 | about $0.05 | 1 min 23 s |

Costs for the OpenRouter rows are the token counts above multiplied by OpenRouter's list prices on
2026-11-09, which were $0.10 and $0.50 per million for Haiku, $0.09 and $0.18 for DeepSeek flash, $0.96 and
$1.91 for DeepSeek pro. Token counts differ between vendors because tokenisers differ. DeepSeek flash's
output count almost certainly includes reasoning tokens.

Reading: Haiku 5.5 asserted the same rows Sonnet did at about a thirtieth of the cost and finished in
under half a minute. DeepSeek pro said almost nothing. DeepSeek flash was slow and verbose. On these
numbers Haiku through OpenRouter is the judge to put in CI, and Sonnet stays the reference the eval set
was labelled with.

What is not yet measured: how the cheaper judges do on rows labelled CONFLICT and UNCLEAR. The only corpus
with those rows is private, and sending its diffs to a third-party endpoint is a decision its owner has
not taken. Until a public corpus with planted conflicts exists, treat the table above as a cost and
latency comparison, not a quality one. Run files for these rows are in
[the cheap-judges spike](spikes/2026-11-09-cheap-judges.md).

## Keeping the bill bounded

- One judge call per commit in the range. A pull request with forty commits is forty calls. `--max-calls N`
  (Action input `max-calls`) judges the first N and reports the rest as not judged, with a problem line per
  skipped commit, so a capped run is visibly partial rather than quietly green.
- A commit that touches nothing an ADR governs costs no call at all. Tight `Applies to` globs or a
  `.adrcheck/map.toml` are the cheapest cost control there is.
- An OpenRouter key carries an optional credit limit, set when the key is created. Once it is spent,
  requests with that key are rejected. OpenRouter's own docs recommend a limit on every key, because a
  key without one can spend the whole balance. Give CI a limited key.
- The Anthropic console sets a spend limit on the Billing page, anywhere below the tier's cap. Requests
  stop at the limit.
- A model that cannot be reached is exit 3, a warning, never a failed build. Nothing retries.

## In the GitHub Action

The Action passes `inputs.model` straight to `--model` and inherits the environment of the step that
calls it, so any provider works. For OpenRouter:

```yaml
- uses: kevin-burns/adrcheck@main
  env:
    OPENAI_BASE_URL: https://openrouter.ai/api/v1
    OPENAI_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
  with:
    model: openai:anthropic/claude-haiku-5.5
```

Ollama from a hosted runner means the runner must reach your machine over the network and the machine
must be awake whenever a pull request arrives. Keep Ollama for the compile seat and for local runs.
