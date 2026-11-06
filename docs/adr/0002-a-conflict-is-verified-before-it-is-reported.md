# 2. A conflict is verified against the diff and the ADR before it is reported

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/domain/verify.py, src/adrcheck/usecases/check.py, src/adrcheck/adapters/claude_judge.py

## Context

A model asked whether a change breaks a decision will sometimes cite a line the change did not
touch, or a sentence the ADR does not contain, or a sentence from the Context or Considered
Options sections that never bound anyone. In the first spike 4 of 28 claims cited a line outside
the diff.

## Decision

Every CONFLICT carries a changed line and a verbatim quote from the ADR. `verify()` in
`src/adrcheck/domain/verify.py` checks both before the verdict stands: the line must be in the
change, the quote must be in the ADR, and the quote must come from a section named in
`BINDING_SECTIONS`, which is the Decision and Consequences sections and nothing else. A CONFLICT
whose claim fails verification is downgraded to UNCLEAR with the failure named. No code path
reports a CONFLICT that skipped `verify()`.

## Consequences

Context and Considered Options can never produce a conflict. A weaker judge degrades to more
UNCLEAR findings, not to more false conflicts. The judge prompt must ask for the line and the
quote in the exact form `verify()` compares.
