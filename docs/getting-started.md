# Getting started

adrcheck reads the architecture decision records in a repository and judges code changes against them.
It answers two questions. Does this change break a decision we wrote down? And has the code moved on from
a decision we never updated? This page gets you from nothing to a first report and tells you what each
line of it means.

Two words recur. The **compiler** is the model call that turns one ADR into obligations, once. The
**judge** is the model call that reads one commit against the obligations of every ADR that applies to it.
Everything else adrcheck does is deterministic.

You need: a git repository with ADRs as numbered markdown files, Python 3.13 or later with `uv`, and one
model provider. The default provider is the Anthropic API when `ANTHROPIC_API_KEY` is set, else a logged-in
Claude Code install. Other providers, including cheaper ones, are on the [providers page](providers.md).
No provider at all is fine for step 1; steps 2 and 3 print `could not evaluate` with the reason and exit 3
when none is reachable.

## Step 1: run it without a model

One command costs nothing and tells you whether your ADRs are in a shape adrcheck can read.

```sh
uv tool install git+https://github.com/kevin-burns/adrcheck
adrcheck lint
```

Or run it once without installing: `uvx --from git+https://github.com/kevin-burns/adrcheck adrcheck lint`.

adrcheck looks for ADRs in the first of `docs/adr`, `docs/decisions`, `docs/architecture/decisions`, `doc/adr`, `doc/architecture/decisions`, `adr`, `adrs`, `decisions` that exists. Pass `--adr-dir` if yours live elsewhere.

What you should see on a healthy set:

```text
ADR set is clean
```

Anything else is a hygiene finding, one per line, with a code such as `missing-status` or
`dangling-supersede-ref`. Each code is explained on the [verdicts page](verdicts.md#hygiene-codes). Fix
these first. An ADR with no recognisable status, or no decision section, cannot bind anything.

## Step 2: compile the ADRs into obligations

```sh
adrcheck compile
```

This is the one step that reads every ADR with a model. For each ADR it writes a list of obligations: the
concrete things the decision requires or forbids, each with the sentence of the ADR it came from. The
result is cached under `.adrcheck/obligations/`, keyed by the ADR's text, so an unchanged ADR is never
compiled twice. Commit that directory. Your colleagues and CI then pay nothing for compile.

What you should see, from adrcheck's own ADR-1:

```text
ADR-1: The domain imports no adapters, use cases, CLI or I/O libraries [accepted]
  ADR-1/1 [MUST_NOT, mechanical] Modules under src/adrcheck/domain/ must not import adrcheck.adapters.
      quote: 'They never import `adrcheck.adapters`, `adrcheck.usecases`, `adrcheck.cli`, `subprocess`, `requests` or `httpx`.'
      mandates=[] forbids=['import adrcheck.adapters', 'from adrcheck.adapters', 'from adrcheck import adapters']
  ...
  ADR-1/8 [MUST, structural] Every dependency the domain or use cases need from the outside world is declared as a Protocol in src/adrcheck/ports.py.
      quote: 'Every dependency the domain or use cases need from the outside world is a `Protocol` in `src/adrcheck/ports.py`'
      mandates=['src/adrcheck/ports.py', 'Protocol'] forbids=[]
```

The last line, on stderr, is `model cost this run: $0.0000 (cached ADRs cost nothing)` when every ADR was
already compiled.

Read this output. It is the contract the judge will hold your code to. Each obligation has:

- a kind, `MUST` or `MUST_NOT`;
- a checkability: `mechanical` (an import, a path, visible in a diff), `structural` (a boundary or dependency
  direction, needs module context), `intent` (behavioural; the judge will lean to UNCLEAR unless the diff
  is explicit) or `process` (a team practice, listed and never judged);
- the quote it was compiled from, which must come from the Decision or Consequences section;
- anchors: the names and paths it mandates. Two checks that need no model look for these in the code: the
  stale sweep described in step 3, and the parent-commit probes behind the ADR-OVERTAKEN verdict on the
  [verdicts page](verdicts.md#adr-overtaken).

If an obligation surprises you, the ADR is ambiguous, not the compiler. Edit the ADR and compile again. The
[writing ADRs page](writing-adrs.md) shows what compiles well.

## Step 3: judge some commits

```sh
adrcheck check --range origin/main..HEAD --format md --fail-on conflict
```

No provider yet? `adrcheck check --staged` and `--tier free` on any range run without one: forbidden patterns
from the cached compile and the stale sweep, no model. The judged run below needs a provider.

One judge call per commit in the range, carrying every accepted ADR whose `Applies to` paths the commit
touches or whose number the commit mentions, plus every accepted ADR that has no `Applies to` at all, since
nothing says it does not apply. Commits that touch nothing any ADR governs cost no call, which is why the
header matters.

What you should see. This is the report on a commit of the planted corpus that ships with adrcheck
(`evals/planted/build.py`, a toy ledger service), a commit written to break ADR-1 on purpose, judged by Haiku
5.5 through OpenRouter on 2026-11-09. Exit code 2.

```markdown
## 36f6b01e32 fix(billing): fast path reads the balance in one query

- **CONFLICT** ADR-1 (3 obligations: 3 CONFLICT)
  - **CONFLICT** ADR-1/1
    - `services/billing/invoices.py`: `return Money(sum_minor_units(connection(), account))`
    - > Code under `services/billing/` reads and writes ledger entries only through `Ledger` in `ledger/api.py`.
    - The new outstanding_fast reads ledger entries via sum_minor_units on a raw connection instead of through the Ledger class.
  - **CONFLICT** ADR-1/2
    - `services/billing/invoices.py`: `from ledger.db import connection, sum_minor_units`
    - > It never imports `ledger.db`.
    - The added import statement imports ledger.db directly into services/billing code.
  - **CONFLICT** ADR-1/3
    - `services/billing/invoices.py`: `return Money(sum_minor_units(connection(), account))`
    - > Billing cannot tune a query by hand.
    - The new single-query fast path hand-tunes a balance query against the ledger, bypassing the Ledger API the ADR requires.
- **COMPLIANT** ADR-3 (ADR-3/1)
  - `services/billing/invoices.py`: `return Money(sum_minor_units(connection(), account))`
  - > Amounts are instances of `Money` from `libs/money/money.py`, which holds minor units as an integer.
  - The returned balance is wrapped in a Money instance built from the integer result of sum_minor_units.
- proposed, not enforced, touches its paths: ADR-5
```

Every finding has the same four parts: the verdict and which obligation of which ADR; the changed line it
is about; the sentence of the ADR it is held against, as a quote; and the judge's reason in one line. When
one ADR has several findings on a commit they sit under one head line that carries the worst verdict and
the tally, as ADR-1 does above; a lone finding stays on one line, as ADR-3 does. ADR-5 is Proposed, so the
change touching its paths is noted and nothing is enforced.

Other trailing lines you will see: `compliant, nothing to cite` for ADRs the judge passed without naming a
line; `judged, not relevant` for ADRs it was shown and set aside; `uncovered files`, the count of changed
files that none of the judged ADRs' `Applies to` globs matched. A high uncovered count on a large change is
a hint that your globs are narrower than your code.

A second section appears when something is stale:

```markdown
## Possibly overtaken ADRs (named anchors missing at the end of the range)

- ADR-9 ADR-9/4: missing 'ChatRunner', 'ChatRequest', 'ChatReply'
```

This is the stale sweep. It is not about the commits you checked: once per run, at the end of the range,
adrcheck looks for every anchor every accepted ADR mandates, and an obligation whose anchors are all gone
from the code is listed. On a repository with history this list is long the first time. The
[verdicts page](verdicts.md#the-stale-list) defines it and the [use cases page](use-cases.md) covers
reviewing it once and keeping it as a baseline.

## Exit codes

0 is nothing to act on, 2 is a verified CONFLICT and only with `--fail-on conflict`, 3 is could not
evaluate. The full table per command is on the [verdicts page](verdicts.md#exit-codes). In the GitHub
Action, 3 is reported as a warning and does not fail the step; in a shell or a pre-commit hook it is a
non-zero exit like any other, so decide there whether an unreachable model should block you.

## One more command

```sh
adrcheck explain --adr 7
```

Takes one ADR and prints each obligation with where its anchors live in the code right now, and marks the
obligations whose anchors are all gone. No judge call. The [use cases page](use-cases.md) shows it in the
architect's sequence.

## Where to next

- [What the verdicts mean](verdicts.md), including the ones that are not verdicts.
- [The flow](workflow.md), as diagrams: what happens inside one run, and what a team does around it.
- [Use cases](use-cases.md): joining a repository with ADRs, bringing ADRs to a repository with history,
  running in a pull request, running before commit.
- [Writing ADRs that compile](writing-adrs.md).
- [Providers and cost](providers.md).
