# 6. An exception trailer waives an ADR only with a reason

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/domain/exception.py, src/adrcheck/usecases/check.py

## Context

Sometimes a change knowingly breaks a decision: a one-off backfill, a migration, a deliberate
exception. The author needs a way to say so that the checker honours and the reviewer can read.

## Decision

A commit message trailer of the form `Adr-Exception: ADR-NNNN <reason>` waives that ADR for that
change. `parse_exceptions()` in `src/adrcheck/domain/exception.py` accepts the trailer only when a
reason follows the ADR number; a trailer without a reason is reported as a problem and waives
nothing. A waived ADR is reported as COMPLIANT with the reason shown, so the waiver is visible in
the report, never silent.

## Consequences

Every exception is on the record in git history and in the report. The trailer is per commit, so
a waiver does not leak into later changes.
