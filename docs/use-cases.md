# Use cases

Five situations, by who you are and what the repository already has. Each ends with the commands and
what to expect from them.

## You joined a team that keeps ADRs

You are new. The repository has a `docs/adr/` with twenty records and you have not read them. adrcheck
is the fastest way to find out which ones your change touches, without reading all twenty.

Make your change. Before committing, run it against the index:

```sh
adrcheck check --staged --format md
```

Check that `.adrcheck/obligations/` is in the repository first. If it is, the ADRs are already compiled
and the run costs one judge call; if not, your first run compiles every ADR that applies, on your key.

Three things the report tells you that the ADRs alone do not:

- **Which decisions govern the files you touched.** ADRs whose `Applies to` matches your paths, or whose
  number your commit message mentions, reach the judge, along with any ADR that has no `Applies to` and so
  might apply anywhere. The rest are not shown. The report is your reading list.
- **What the decision actually requires.** Each finding quotes the sentence of the ADR it is held against. You
  can read the one sentence that matters instead of the whole record.
- **Whether your change keeps to it.** COMPLIANT with a reason is a free review. CONFLICT with a quote is a
  conversation you can have before the pull request, with the ADR open.

If a CONFLICT is right and the decision is wrong, do not route around it. Say so in the commit:

```text
Adr-Exception: ADR-12 the batch endpoint needs the raw rows; discuss superseding ADR-12
```

The waiver is visible in the report and in history, which is how a decision gets reopened honestly.

If the repository has the pre-commit hooks installed, the lint hook runs for free whenever an ADR file changes
and the staged check runs if the team enabled it. Nothing you do on your machine spends the team's key; `--staged`
uses whatever provider your own environment names.

## You are an architect with ADRs and no enforcement

You have forty ADRs, written over three years. Some are still true. Some describe code that was rewritten
twice. You want to know which, and you want new changes checked from now on. This is the brownfield case
and it has an order.

**Lint first.** No model, no cost.

```sh
adrcheck lint --adr-dir docs/adr
```

Expect findings. ADRs written over years have missing statuses, supersede chains that never updated the
old record, and files with no Decision heading. Fix these. Nothing without a status is enforced and nothing
without a binding section can be.

**Compile and read.** One model call per ADR, cached forever by the ADR's text.

```sh
adrcheck compile --adr-dir docs/adr
```

Read the obligations. This is the step architects underestimate. The compiler turns prose into
`MUST`/`MUST_NOT` statements with named anchors, and it is faithful to what the ADR says, not to what you
meant. An ADR that says "services should prefer the event bus" compiles to very little. One that says
"services publish to `events.topic` and never call each other's HTTP endpoints" compiles to obligations the
judge can hold code to. Where an obligation surprises you, the record is ambiguous. Edit it and compile
again. The [writing ADRs page](writing-adrs.md) has the patterns.

**Scope the ones with no `Applies to`.** An ADR with no paths is shown to the judge on every commit, and
dismissed on most of them at your expense. Add an `Applies to:` header line, or keep paths out of the
records and in a repo-side map:

```toml
# .adrcheck/map.toml
[[adr]]
id = 7
paths = ["services/billing/**", "libs/money/**"]
```

The header wins where both exist, and lint reports the disagreement.

**Run a sweep over history and read the stale list.**

```sh
adrcheck check --adr-dir docs/adr --range v2.0..HEAD --format md > first-run.md
```

Every commit in the range that touches a governed path is one judge call, so pick a range you can count.
Fifty commits on Haiku is about half a dollar; on Sonnet it is many times that. The stale list is computed
at the end of the range whatever its length, so a short range still gives you the full stale picture.

The findings tell you how recent commits did against the decisions. The stale list at the end tells you
which decisions the code has left behind entirely. Expect it to be long. For each row: supersede the ADR if
the decision is dead, fix the anchors if the ADR named the wrong thing, or accept the row. Then record what
you accepted:

```sh
adrcheck check --adr-dir docs/adr --range origin/main..HEAD --write-baseline
git add .adrcheck/obligations .adrcheck/baseline.json
git commit -m "docs(adr): adrcheck obligations and reviewed stale baseline"
```

**Then turn on the pull request check.** From this point every PR gets one comment and a verified CONFLICT
can fail the step. The README has the workflow file; the [providers page](providers.md) has the cheaper
judges and how to cap the key.

What you get back as an architect: the records stop being documentation and start being a contract that
is checked at the moment code changes, and the stale list is a standing answer to "which of our
decisions are still true".

## You want ADRs checked in every pull request

Add the Action. The README shows the workflow. The Action does not discover the ADR directory; its
`adr-dir` input defaults to `docs/adr`, so set it if yours differs. Three things worth deciding up front:

- **Which judge.** The cheapest judge measured so far was Haiku 5.5 through OpenRouter, at about a cent per
  commit. It asserted the same COMPLIANT rows Sonnet did; its behaviour on conflicts is not yet measured.
  See [providers](providers.md).
- **A call cap.** `max-calls: 10` judges the first ten commits of a pull request and reports the rest as not
  judged. The comment says so; nothing is silently green.
- **Whether CONFLICT fails the step.** It is on by default. A team adopting on history may want it off for
  the first weeks, reading the comment instead, until the baseline settles.
- **Who can waive.** The `Adr-Exception` trailer is in the commit message, so the reviewer sees it. Decide
  whether a waiver needs a second approver.

What appears: one comment per pull request, replaced on every push, with the findings grouped by commit
and the stale list under them. A comment is posted even when no ADR applied, so a quiet run is visible rather
than missing.

## You want to know when a decision was left behind

The ADR says the importer is the single entry point. The code has no importer. When did that happen and
was it deliberate? Check a range and read the verdicts in order.

```sh
adrcheck check --range v1.4..v1.8 --format json > sweep.json
```

The commit that removed the importer shows CONFLICT against that ADR if the importer was still in use, or
ADR-OVERTAKEN with the note "removed anchor had no callers at parent" if the importer had already become
dead code. Any later commit the judge flags against that ADR shows ADR-OVERTAKEN, because the anchor was
already gone at its parent, and the stale list at the end of the report names the ADR too. The change in
verdict is the commit you are looking for. Whether it carried an `Adr-Exception` trailer tells you whether
it was deliberate.

## You are changing the prompts or the rules

Frozen cases under `evals/cases/` are the measurement. Each is a commit, an ADR, the quote and the agreed
verdict. Run a corpus and score it in one command:

```sh
adrcheck eval --cases evals/cases/adrcheck.json --run --report /tmp/after.json
```

Exit 0 when every row hits. Compare input tokens across runs, not dollars, when the judge runs through the
Claude CLI; its cache state makes per-run cost noisy. A corpus of only COMPLIANT rows cannot tell a careful
judge from a silent one. The planted corpus has the CONFLICT rows: build it with `evals/planted/build.py`,
export `ADRCHECK_EVAL_PLANTED_REPO`, and run `evals/cases/planted.json` the same way.
