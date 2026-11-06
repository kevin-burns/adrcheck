# 7. A contradiction already present at the parent commit is ADR-OVERTAKEN, not CONFLICT

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/domain/overtaken.py, src/adrcheck/usecases/check.py

## Context

When code and ADR disagree, one of them is wrong. If the disagreement existed before this change,
the change did not cause it; the ADR has been overtaken by the codebase and the finding belongs to
the ADR's author, not the commit's.

## Decision

`classify()` in `src/adrcheck/domain/overtaken.py` turns a judge's CONFLICT into ADR-OVERTAKEN
when the contradiction can be shown at the parent commit: a named anchor the ADR mandates was
already absent, or the cited line already existed elsewhere in the code at the parent. The
`RepoReader.contains()` probe answers those questions against the parent ref. ADR-OVERTAKEN never
fails the build.

## Consequences

The author of a change is not blamed for history. The probes are cheap and deterministic. The
case of a removal of code that had no callers at the parent is not yet covered and is tracked in
bead adrcheck-ihg.
