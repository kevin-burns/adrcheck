# Spike: the OpenAI-compatible runner against Ollama on the M5

Date: 2026-11-08, late evening. Bead adrcheck-oao, item 2. Host reached by name, never by address.

## What ran

| Step | Model | Result | Time |
|---|---|---|---|
| transport smoke, one word | qwen2.5:0.5b | `Okay.`, 20 in / 3 out, cost 0 | 749 ms |
| compile ADR-6 (exception trailer) | qwen3.6:27b-coding | HTTP 500: needs 17.5 GiB, 17.3 GiB free | 0.2 s |
| compile ADR-6 | qwen3.5:9b-q8_0 | 3 obligations, parsed by the shared parser | 4 min 14 s, cold load |

The 9B compile produced the same shape Sonnet produces: a MUST on the reason requirement, a MUST NOT on a
bare trailer waiving nothing, a MUST on the waiver being visible, each with a verbatim quote that verify()
would accept. All three anchor on the parser module path, which is weaker than Sonnet's anchors but true.
The four minutes include loading a 9B model from cold on a shared machine; no warm figure was taken.

## What it taught

- The parser and prompt are provider-neutral in practice, not only by construction (ADR-9): a 9B local
  model's reply went through unchanged.
- Ollama's error body is the diagnosis (`model requires 17.5 GiB but only 17.3 GiB are available`), and the
  runner threw it away behind a urllib traceback. Fixed the same evening: HTTP errors carry the endpoint's
  message, and `compile` exits 3 with the reason like `check` does.
- No judge run was attempted locally: a judge prompt is ~90k tokens and a 9B model on this machine would
  take tens of minutes per commit. Local models fit the compile seat (once per ADR, cached) and the gate
  (bead c6l), not the judge seat, until the prompt is smaller.
