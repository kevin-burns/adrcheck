# 11. Scope comes from the ADR header first and a repo-side map second; the header wins

Date: 2026-11-08
Status: Accepted
Bead: adrcheck-yi8
Applies to: src/adrcheck/domain/scope.py, src/adrcheck/adapters/scope_map.py

## Context

An ADR with no `Applies to` line rides every commit to the judge. On i-dot-ai/consult none of the
sixteen ADRs carried one, so a one-line CODEOWNERS edit cost a full judge call. Many teams cannot add
the line: the ADRs are a Confluence export, an archive, or another team's wiki. The idea of a
repo-side map is borrowed from adr-guard (MIT); the glob language and precedence are adrcheck's.

## Decision

`.adrcheck/map.toml` holds `[[adr]]` rows of `id` and `paths`, the same glob subset `Applies to`
accepts. The domain function `scope()` fills `applies_to` for an ADR that has none from the map. When
both exist and differ, the header stands and lint reports `scope-disagreement`; a map row for an ADR
that does not exist is `map-unknown-adr`. `check` prints the same issues as warnings and continues.
The map is keyed by ADR number, so two records sharing a number share a scope, and lint already
reports the duplicate. A changed file no ADR covers stays counted as uncovered.

## Consequences

A brownfield team scopes its decision log without editing it, and a CODEOWNERS edit costs nothing.
Two sources of one fact is a defect in the ADR set, reported rather than merged quietly. A wrong map
hides a conflict exactly as a wrong header does; the map is reviewed like source.
