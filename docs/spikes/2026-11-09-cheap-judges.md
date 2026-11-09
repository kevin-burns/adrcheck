# Cheaper judges through OpenRouter, 2026-11-09

Question: can the judge seat run on something cheaper than Sonnet without a code change, and what does
it cost? The `openai:` runner pointed at `https://openrouter.ai/api/v1`, the frozen adrcheck corpus
(`evals/cases/adrcheck.json`, one commit, eleven COMPLIANT rows), compile seat from the committed Sonnet
obligation cache in every run.

| Judge | Hits | Asserted | Tokens in / out | Wall time | Run file |
|---|---|---|---|---|---|
| claude-cli:sonnet (2026-11-08) | 11/11 | 6 | 108,549 / 2,831 | not timed | `.cheap-judges.sonnet.run.json` |
| openai:anthropic/claude-haiku-5.5 | 11/11 | 6 | 58,655 / 6,611 | 28 s | `.cheap-judges.haiku.run.json` |
| openai:deepseek/deepseek-v4-flash | 11/11 | 3 | 40,898 / 26,916 | 5 min 38 s | `.cheap-judges.deepseek-flash.run.json` |
| openai:deepseek/deepseek-v4-pro | 11/11 | 1 | 40,819 / 7,446 | 1 min 23 s | `.cheap-judges.deepseek-pro.run.json` |

"Asserted" is the number of rows the judge named COMPLIANT. The rest were quiet, which the scorer counts
as a hit when the label is COMPLIANT. A corpus with no CONFLICT rows cannot separate a careful judge from
a silent one; this spike measures cost and latency, not quality.

OpenRouter list prices on the day, per million tokens in / out: Haiku 5.5 $0.10 / $0.50; DeepSeek v4
flash $0.09 / $0.18; DeepSeek v4 pro $0.96 / $1.91. The Sonnet row's $0.31 is the figure the claude CLI
reported.

Haiku asserted the same six rows Sonnet did. DeepSeek flash's output count is almost certainly reasoning
tokens, which also explains the five minutes.

Not done: the same four judges on the job-search corpus, which holds the CONFLICT and UNCLEAR rows. That
repo holds personal data and its diffs have so far only gone to Anthropic; sending them through OpenRouter
is the owner's decision.

Rolling guidance lives in [docs/providers.md](../providers.md); this file is the measurement behind it.
