# The planted corpus and four judges, 2026-11-09

Question: with labels that are true by construction, do cheaper judges catch planted conflicts, or only
stay quiet on compliant commits? The morning's cheap-judge spike could not answer this because the adrcheck
corpus has no CONFLICT rows.

`evals/planted/build.py` builds a toy ledger service: five ADRs, nine commits, pinned author and dates so
the hashes are stable. Four commits break a decision on purpose, one waives a breach with an
`Adr-Exception` trailer, one changes only the README, one deletes an importer nothing called, one touches a
Proposed ADR's paths. `evals/cases/planted.json` holds nine labelled rows and one expected stale ADR.
Compile seat: Sonnet via the Claude CLI on the first run, cached for the rest, so the table compares judges.

## First run, before the rule change

Sonnet scored 8/9. The miss was the deleted importer: expected ADR-OVERTAKEN, got UNCLEAR, reason "The
diff deletes the mandated entry point, but it shows no callers and no post-change files, so I can't tell
whether this leaves CSV ingestion with no entry point or removes dead code." The dead-removal probe of
ADR-7 knew the answer and did not run, because it only ran on a CONFLICT. ADR-7 was amended so the third
probe also settles an UNCLEAR about a removed line (commit 20029f3). A COMPLIANT is never changed.

## Second run, four judges

| Judge | Route | Score | Tokens in / out, 7 calls | Cost | Wall |
|---|---|---|---|---|---|
| claude-sonnet-5-5 | claude-cli | 9/9 | 359,851 / 2,851 | $0.065 reported | 58 s |
| anthropic/claude-haiku-5.5 | OpenRouter | 9/9 | 10,593 / 6,015 | about $0.004 | 33 s |
| deepseek/deepseek-v4-flash | OpenRouter | 9/9 | 7,312 / 7,833 | about $0.002 | 1 min 3 s |
| deepseek/deepseek-v4-pro | OpenRouter | 9/9 | 7,549 / 17,729 | about $0.04 | 14 min 7 s |

Run files beside this page: `.planted.sonnet.run.json`, `.planted.haiku.run.json`,
`.planted.deepseek-flash.run.json`, `.planted.deepseek-pro.run.json`. OpenRouter costs are the token
counts times the list prices read on 2026-11-09 (Haiku $0.10 / $0.50 per million, flash $0.09 / $0.18, pro
$0.96 / $1.91).

Every judge found all three planted conflicts and honoured the waiver. The README-only commit made no call
under any judge. The stale list named ADR-4 three times, once per obligation whose anchors were gone.

## What the token column says about the CLI route

Same corpus, same prompts, same cached obligations: the Claude CLI reported 359,851 input tokens for seven
calls, about 51,000 a call, and Haiku through the API reported 10,593, about 1,500 a call. The prompts
adrcheck sends are the same size on both routes. The difference is fixed per call and far larger than any
diff in this corpus, which is consistent with `claude -p` counting its own system prompt and tool
definitions as input on every call. Not verified against the CLI's internals; the measurement is what it
is. Two consequences: compare token counts within one route only, and the CLI route costs more per call
than the model's list price would suggest.

## Limits

Nine rows and one toy codebase. The planted breaches are the obvious kind, an import and a float. A judge
that passes this corpus has shown it can read a diff against a quoted sentence; it has not shown it can
tell a subtle breach from a refactor. The next corpus should plant those: a boundary crossed through a
helper, a forbidden call behind an alias, an anchor moved rather than removed.
