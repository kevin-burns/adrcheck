# 2. Fold rows, never drop them

## Issue

Rows deleted after triage return as new on the next sweep and the counts drift.

## Decision

A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built
from, carries its reason, and is counted.

## Status

Accepted

## Group

Data pipeline

## Assumptions

Sweeps repeat and adverts recur.

## Constraints

The report must still hide folded rows by default.

## Positions

Drop rows the triage says no to. Keep a separate archive table. Fold rows in place with a reason.

## Argument

Folding in place keeps one store and one count.

## Implications

Every pile is listed, never hidden. Storage grows with history.

## Related decisions

ADR-1, one canonical row key.
