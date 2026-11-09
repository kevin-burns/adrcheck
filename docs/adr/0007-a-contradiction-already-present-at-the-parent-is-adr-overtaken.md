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
already absent, the cited line already existed elsewhere in the code at the parent, or the cited
line removes a named anchor that nothing but its own definition referenced at the parent. The
`RepoReader.contains()`, `RepoReader.has_line()` and `RepoReader.occurrences()` probes answer those
questions against the parent ref: `contains()` for an anchor, `has_line()` for the cited line as a whole
line, because a substring hit inside a longer line or a string literal is not the same line, and
`occurrences()` for the callers. The third probe also settles a judge's UNCLEAR about a removed line: a judge that sees
only the diff cannot know whether a deleted name had callers, and the count can. A COMPLIANT verdict
is never changed by any probe. ADR-OVERTAKEN never fails the build.

## Consequences

The author of a change is not blamed for history, and deleting dead code is not breaking a decision:
the decision had already been left behind. The probes are cheap and deterministic; the occurrence
count is a whole-identifier match over the parent's code text, so a definition alone counts as one.
Amended 2026-11-08 for the third probe (bead adrcheck-ihg).
