# 2. Fold rows, never drop them

## Status

Accepted

## Submitters

The pipeline owner

## Context

Rows deleted after triage return as new on the next sweep and the counts drift.

## Proposed Design

A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built
from, carries its reason, and is counted.

## Decision

Approved as proposed.

## Consequences

Every pile is listed, never hidden. Storage grows with history.

## References

ADR-1
