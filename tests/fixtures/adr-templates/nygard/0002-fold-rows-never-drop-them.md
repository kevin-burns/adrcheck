# 2. Fold rows, never drop them

Date: 2026-11-08
Status: Accepted
Applies to: enrich/**

## Context

Earlier sweeps deleted rows the triage said no to. A later sweep found the same advert and the row came
back as new, so counts drifted and nobody could tell what had been seen before.

## Decision

A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built
from, carries the reason it was folded, and is counted. A duplicate folded into another row keeps its link
on the surviving row. The only rows that may leave the data are ones whose source has withdrawn them.

## Consequences

Every pile is listed, never hidden. Counts in the report are stable across sweeps. Storage grows with
history, which is accepted.
