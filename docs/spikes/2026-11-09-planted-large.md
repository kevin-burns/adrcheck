# The large planted corpus: sixteen ADRs, the breaches a reviewer argues about, three judges, 2026-11-09

Kevin's point after the first real catch: adrcheck had been proven against five toy ADRs and one small real
set, not against a project with many records. `evals/planted/build_large.py` is the answer: a toy orders
service with sixteen ADRs (thirteen Accepted, one Superseded, one Proposed, one Deprecated) and twenty
commits. Where the small corpus plants an import and a float, this one plants what people argue about in
review: a forbidden import behind an alias and behind `importlib`; a boundary crossed through a helper; the
forbidden word inside a string literal and inside a comment; an anchor whose body moves to another module;
an edit under a superseded record; a trailer naming a record that does not exist; two records broken in one
commit; a breach whose identical line already sits on the base; and a dead-code deletion that leaves a
record stale. `evals/cases/planted-large.json` holds 25 labelled rows, written before any judge ran.

## The first run changed two rules and one label

Haiku 5.5 through OpenRouter scored 19/25. The six misses were three rows lost to rules of ours, one to a
label of mine, and two to the judge:

- **Three rows were rules of ours.** The precedent probe (ADR-7's second question, "did this line already exist at
  the parent?") used a substring match, so `import requests` was found inside `import requests as http` and
  inside a log message that said "import requests is not allowed here", and a planted CONFLICT became
  ADR-OVERTAKEN. `RepoReader.has_line()` now matches a whole line. And the self-contradiction rule turned a
  verified CONFLICT into UNCLEAR whenever another obligation of the same ADR passed the same line. On
  `fetch(u, timeout=None)` the call routes through `fetch()` (one obligation kept) and passes `timeout=None`
  (another broken); both verdicts are right. The CONFLICT now stands and its note names the sibling. That
  rule had hidden two planted CONFLICTs, the `/health` route and `timeout=None`; the precedent bug hid one.
- **One was my label.** The fixture's init commit holds an old domain module that imports the database, a
  deliberate pre-existing sin for a later trap. The commit that adds a second such import therefore repeats
  a line already on the base, and by ADR-7 that is ADR-OVERTAKEN, not CONFLICT. Relabelled, with the reason
  in the row's note.
- **Two were the judge's.** An honest UNCLEAR on a compliant domain refund, and a body moved to a reader
  module read as a second entry point. Those two remain after the fixes, which is the 23/25.

A separate flaw surfaced in the same run: `occurrences()` counted the file-path listing as code, so a
function living in a module named after it (`retry` in `retry.py`) always had two occurrences and could
never be dead. It now counts file contents only.

## Second run, three judges, same rules

| Judge via OpenRouter | Score | Tokens in / out, 19 calls | Wall | Misses |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | 23/25 | 51,649 / 22,391 | 1 min 48 s | UNCLEAR on a compliant domain refund; moved body read as a second entry point |
| anthropic/claude-sonnet-5.5 | 23/25 | 51,649 / 7,961 | 58 s | UNCLEAR on the domain-sibling trap; moved body read as a second entry point |
| deepseek/deepseek-v4-flash | 19/25 | 35,602 / 37,902 | 5 min 17 s | missed the `importlib` import and the missing idempotency key; two false CONFLICTs, the domain sibling and the moved body; called a dead-code deletion COMPLIANT; cited `import os` for the `os.environ` breach, which the precedent probe then found on the base |

Run files beside this page: `.planted-large.haiku-run1.run.json` (before the rule fixes),
`.planted-large.haiku.run.json`, `.planted-large.sonnet.run.json`, `.planted-large.flash.run.json`. The
small corpora were rerun with Haiku after the rule fixes and stayed at 9/9 and 11/11.

## What it says

- The small corpora could not separate these judges; this one does. Haiku and Sonnet agree on 23 and
  differ only in which honest UNCLEAR they give. Flash misses two planted breaches outright and raises two
  false CONFLICTs.
- Every planted breach that depends on reading an import, an argument, a route string or a raise was caught
  by Haiku and Sonnet. The two misses that remain for them are a refactor read too literally and an
  abstention; neither is a false CONFLICT.
- The traps held: the string literal, the comment, the superseded record and the deprecated record produced
  no false alarm from any judge.
- Corpora with planted breaches find bugs in the rules, not only in the judge. Two probes and one counting
  function were wrong before this corpus existed, and the first small corpus had not shown it.

## Limits

Still a toy, still Python, still one author's idea of subtle. The eval workflow runs this corpus as an
informational job: its score is reported on every pull request that touches the rules, and it does not
block, because a judge is allowed to miss here and the number is the measurement.
