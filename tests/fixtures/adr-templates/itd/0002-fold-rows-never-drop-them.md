# 2. Fold rows, never drop them

Status: accepted

## Issue

Rows deleted after triage return as new on the next sweep.

## Alternatives

Drop rows the triage says no to. Keep a separate archive table.

## Decision

A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built
from, carries its reason, and is counted.

## Arguments

One store, one count.

## Implications

Every pile is listed, never hidden. Storage grows with history.
