# 5. Stale ADRs are found by a per-run sweep of named anchors, not by the diff

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/usecases/check.py, src/adrcheck/adapters/git_changes.py

## Context

An ADR whose code was removed months ago is never touched again by a diff, so a checker that only
looks at changes never sees it. The first spike's planted stale ADR was missed at every later
commit until a sweep was added.

## Decision

`stale_sweep()` in `src/adrcheck/usecases/check.py` runs once per `check` invocation, at the end
of the range, over every accepted ADR: an obligation whose named anchors are all missing from the
code at that ref is reported as stale, with no model call. Presence is tested against code only:
`strip_python_prose()` blanks comments and docstrings before the search, and files with
extensions in `_PROSE` are skipped, so a mention in a docstring or a markdown file never counts
as the code still existing. Files under `.adrcheck/` are skipped too: the compiled obligations name
every anchor, and a committed cache must not satisfy its own sweep.

## Consequences

Stale detection is free and deterministic. An ADR that names no anchors cannot be swept and is
reported as such. The sweep reads the whole tree at one ref; its cost on large repositories is
tracked in bead adrcheck-zsj.
