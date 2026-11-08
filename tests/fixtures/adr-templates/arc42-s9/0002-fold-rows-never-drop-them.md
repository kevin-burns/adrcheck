# 2. Fold rows, never drop them

Status: accepted

## Problem

Rows deleted after triage return as new on the next sweep.

## Constraints

The report hides folded rows by default.

## Considered Alternatives

Drop rows the triage says no to; keep a separate archive table.

## Decision

A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built
from, carries its reason, and is counted.

## Justification

One store, one count, no drift.

## Consequences

Every pile is listed, never hidden. Storage grows with history.
