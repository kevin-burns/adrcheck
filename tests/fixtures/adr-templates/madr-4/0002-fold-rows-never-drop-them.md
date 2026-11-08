---
status: accepted
date: 2026-11-08
decision-makers: the pipeline owner
applies_to:
  - enrich/**
---

# Fold rows, never drop them

## Context and Problem Statement

Earlier sweeps deleted rows the triage said no to, and a later sweep brought the same advert back as new.
How do we keep counts stable while still hiding rows from the report?

## Decision Drivers

* Counts must not drift between sweeps
* A reader must be able to see why a row is not shown

## Considered Options

* Fold rows into the data with a reason
* Drop rows the triage says no to
* Keep a separate archive table of dropped rows

## Decision Outcome

Chosen option: fold rows with a reason. A row the pipeline decides not to show is folded, not dropped: it
stays in the data the report is built from, carries the reason, and is counted. A duplicate folded into
another row keeps its link on the surviving row.

### Consequences

* Good, because every pile is listed, never hidden
* Bad, because storage grows with history

### Confirmation

The report lists a count per pile and the folded rows remain in the store; a reviewer checks both after
each sweep.

## Pros and Cons of the Options

### Drop rows the triage says no to

* Good, because the store stays small
* Bad, because the same advert returns as new on the next sweep

## More Information

Revisit when the store exceeds what a single file can hold.
