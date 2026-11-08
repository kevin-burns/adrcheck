# 2. Fold rows, never drop them

Status: accepted

## Problem Statement

Rows deleted after triage return as new on the next sweep and the counts drift.

## Options

Drop rows the triage says no to. Keep a separate archive table. Fold rows in place with a reason.

## Recommendation

A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built
from, carries its reason, and is counted.

## Costs

Storage grows with history.

## Benefits

Every pile is listed, never hidden, and counts are stable across sweeps.

## Risks

A folded row may be missed by a reader who only looks at the report.
