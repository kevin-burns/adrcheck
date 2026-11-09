# An ADR template that compiles

Copy the block below into `docs/adr/NNNN-short-title.md`. The shape is Nygard's, which adrcheck reads
along with MADR and the other common templates; what makes it compile well is not the headings but the
Decision section: named things, MUST and MUST NOT, one sentence per obligation. The reasons are on the
[writing ADRs page](writing-adrs.md).

```markdown
# 12. Billing never reads the ledger table directly

Date: 2026-03-02
Status: Accepted
Supersedes: ADR-3
Applies to: services/billing/**, libs/ledger/**

## Context

Two outages came from billing code holding a transaction open on the ledger table while waiting on a
network call. The ledger package owns its locking; callers should not see the table. Why this decision was
needed goes here, and only here: nothing in this section binds.

## Decision

Code under `services/billing/` reads and writes ledger entries only through `Ledger` in `ledger/api.py`.
It never imports `ledger.db`.

Amounts cross this boundary as `Money` from `libs/money/money.py`, never as a `float`.

## Consequences

Billing cannot tune a ledger query by hand; every ledger access is observable in one place. A migration
that must read the table once declares it with an `Adr-Exception: ADR-12 <reason>` trailer on its commit.
```

What each part does for the checker:

| Part | Effect |
|---|---|
| `# 12. Title` | the number; the filename's leading digits are the fallback |
| `Status: Accepted` | the only status that is enforced; Proposed is noted, the rest are excluded |
| `Supersedes: ADR-3` | lint checks that ADR-3 says Superseded once this one is Accepted |
| `Applies to:` | which changed paths bring this ADR to the judge; no header means every commit |
| Context | read by the judge for intent, never quoted as binding |
| Decision | compiled into obligations; each sentence that names a thing and says MUST or never is one |
| Consequences | also binding; the right place for the exception rule and for what the decision forbids by implication |

Read the compile output before committing the record:

```sh
adrcheck compile --adr-dir docs/adr
```

For the block above you should see two or three `MUST_NOT` obligations with `ledger.db` and `float` in
their forbids, and `MUST` obligations with `Ledger`, `ledger/api.py`, `Money` and `libs/money/money.py` as
anchors. If you see an obligation compiled from the Context paragraph, the parser did not recognise your
headings; run `lint`.
