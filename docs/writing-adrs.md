# Writing ADRs that compile

adrcheck does not change how you write an ADR. It reads Nygard, MADR, Y-statements, Tyree and Akerman, bold
labels and tables, and binds on the role of a section rather than its heading. What it does change is
which sentences matter. This page is about those sentences.

## Only two sections bind

The Decision section and the Consequences section. Context explains, Decision Drivers explain, Considered
Options can never bind, and a quote from Options is evidence of *not* deciding. Every CONFLICT must quote a
sentence from Decision or Consequences, verbatim, or it is downgraded to UNCLEAR.

So the test for a sentence is: if a reviewer quoted this back to a developer, would it settle the argument?

## Name things

The compiler extracts anchors: file paths, module names, function and class names, flags, config keys. The
stale sweep looks for them in the code. The parent probes look for them at the previous commit. A decision
with no anchors cannot be found stale and cannot be shown to have been overtaken.

Compiles to little:

> Services should prefer asynchronous communication where practical.

Compiles to obligations the judge can hold code to:

> Services publish domain events to `events/outbox.py` and never call another service's HTTP API from
> request handlers under `services/*/api/`.

The second gives the compiler a `MUST` with an anchor, a `MUST_NOT` with a path pattern, and a quote that
survives verification. adrcheck's own ADR-1 reads this way, and its compiled form is on the
[getting started page](getting-started.md#step-2-compile-the-adrs-into-obligations).

## Write obligations as MUST and MUST NOT

The compiler produces two kinds and nothing in between. "Should", "prefer" and "where practical" do not
disappear, but they compile to `intent` obligations, and an intent obligation defaults to UNCLEAR unless
the diff is explicit. A sentence about how the team works rather than what the code does, such as "every
ADR is reviewed by two people", compiles to a `process` obligation, which is listed and never judged. If you mean MUST, write MUST. If you genuinely mean a preference, say so, and expect
UNCLEAR rather than CONFLICT when code goes the other way.

## Filenames and numbers

Every `.md` file in the ADR directory is a record, except the directory's own `README`, `index` and
`template`. The number is read from the title first, in any of `# 1. Title`, `# ADR-001: Title`,
`# ADR 001 Title`, `# [ADR-001] Title` or `# 001 - Title`, and otherwise from the filename:
`0001-title.md`, `ADR-001-title.md`, `adr_001_title.md` and `001.md` all give 1. A leading date such as
`20220819-title.md` or `2026-01-10-title.md` is not a number; put the number in the title for those. Leading
zeros never matter, and `ADR-001`, `ADR 1` and `adr1` in text all refer to record 1. A record with no number
anywhere is still read and gets a `missing-number` lint finding, because nothing can supersede, depend on
or waive it. ADR-12 records this.

## The header lines adrcheck reads

```markdown
# 7. Billing never reads the ledger directly

Date: 2026-03-02
Status: Accepted
Supersedes: ADR-3
Applies to: services/billing/**, libs/ledger/**
```

- **Status.** Proposed, Accepted, Deprecated, Superseded or Rejected; common aliases such as Approved, Decided,
  Draft and Retired are read as those five. Only Accepted is enforced. A
  Superseded record should say by what: `Status: Superseded by ADR-9`. Missing status is a lint finding and
  the record binds nothing.
- **Supersedes.** When you supersede, change the old record's status in the same commit. Lint reports a
  successor whose predecessor still says Accepted, once the successor itself is Accepted.
- **Depends on.** Optional, `Depends on: ADR-2, ADR-3`. Lint reports a dependency on a record that is
  Deprecated, Superseded or Rejected, and one on a record that does not exist.
- **Applies to.** Globs, comma separated, matched with Python's `fnmatch`, where `*` crosses `/`; `dir/**` also matches files directly under
  `dir`. This is the cheapest cost control there is. A commit that touches no governed path makes no model
  call. A record without this header is shown to the judge on every commit and dismissed on most of them.

MADR front matter and `**Status:** Accepted` bold labels are read the same way. A table row `| Status |
Accepted |` too.

## Keep paths out of the record if you prefer

Some teams do not want file paths in a decision record. Put them in `.adrcheck/map.toml` instead:

```toml
[[adr]]
id = 7
paths = ["services/billing/**", "libs/ledger/**"]
```

A header in the record wins where both exist, and lint reports the disagreement, so the map can be adopted
gradually.

## Read the compile output before you commit the ADR

```sh
adrcheck compile --adr-dir docs/adr
```

Every obligation is printed with its kind, its checkability, its quote and its anchors. This is the only
honest review of an ADR: not whether it reads well, but what it will be held to. Where an obligation is
not what you meant, the sentence it quotes is ambiguous. Change the sentence, not the obligation.

Four things to look for:

- An obligation quoting Context or Options. The compiler should not do this, and if it does the record's
  headings are not being recognised. Run `lint`, then check the heading names against the common templates.
- An obligation with no anchors. It will never be found stale and the parent probes cannot help it. Add a
  name.
- An anchor that lives in prose. The stale sweep searches code only, and strips comments and docstrings
  from Python before it looks. For other languages a comment counts as code, and a JSON, YAML or TOML
  mention counts too. Name a function, a class or a path, not a phrase.
- Six obligations from one sentence that lists six things, as adrcheck's ADR-1 does. That is correct and
  useful. Each is checked on its own.

## Deprecating and superseding

Supersede, do not delete. A deleted ADR takes its history with it; a Superseded one is excluded from
enforcement and still explains why the code looked the way it did. The stale list is the usual prompt:
when every anchor an obligation names is gone from the code, the decision has either been abandoned or
needs a successor that names what replaced it.

## Exceptions belong in the commit, not the record

A decision does not need an "unless" clause for every known special case. The commit that makes the
exception says so:

```text
Adr-Exception: ADR-7 the migration reads the ledger once to backfill invoice ids
```

That keeps the record clean and the exception on the record, where a reviewer sees it.
