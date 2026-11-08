# 10. The stale list is reviewed once and kept as a baseline the team edits like source

Date: 2026-11-08
Status: Accepted
Bead: adrcheck-yi8
Applies to: src/adrcheck/domain/baseline.py, src/adrcheck/adapters/baseline_file.py

## Context

The first run on a repository with history lists every accepted ADR whose anchors have left the tree.
On i-dot-ai/consult that was nine obligations across five of sixteen ADRs, and only the maintainers can
say which are renames, which are accepted debt and which are decisions nobody wrote down as reversed.
A list that is the same every run is read once and then ignored, and the one new row in it is missed.
The idea of a reviewed baseline that only new findings escape is borrowed from adr-guard (MIT); the
rows it holds are adrcheck's own.

## Decision

`adrcheck check --write-baseline` records the run's stale list to `.adrcheck/baseline.json`, every row,
keyed by ADR number and obligation id with the missing anchors beside them for the reviewer. Later runs
read the file when it exists, keep the rows it names in the report flagged as known, list only the
others, and print a count of the known. Nothing updates the file except a deliberate `--write-baseline`;
it is committed and reviewed like source. The baseline holds stale rows only. CONFLICT findings are
per diff, and a pull-request range never replays old commits, so a baseline of conflicts would have
nothing to match.

## Consequences

A brownfield team runs once, reviews the list, commits the file, and from then on sees only what moved.
A row leaves the baseline when the team removes it or rewrites the ADR, since an edited ADR compiles to
new obligation ids and its rows surface again for review. The format is versioned so a later key can
be added without breaking an old file.
