# 13. A pull request is judged as the change it merges, not commit by commit

Date: 2026-11-09
Status: Accepted
Applies to: src/adrcheck/adapters/git_changes.py, src/adrcheck/cli.py, action.yml

## Context

adrcheck's second pull request on its own repository put a module in the wrong layer in one commit and
moved it in the next. Judged commit by commit, the first commit was a verified CONFLICT and the third was
COMPLIANT, and the Action failed the pull request for a state that would never reach `main`. The author
had already done what the CONFLICT asked. A gate on a pull request should answer "does what merges keep to
the decisions", and a sweep over history should answer "when did a decision get left behind". Those are
different questions and were being asked with one shape.

## Decision

`GitChanges.combined()` in `src/adrcheck/adapters/git_changes.py` turns a range into one `Change`: the
parent is the merge base, the files are the net diff from merge base to head, and the message is every
commit message in the range joined, so an `Adr-Exception` trailer on any commit waives for the whole
change. A line added in one commit and removed in a later one is not part of the change. `check --range
A..B --as-one` in `src/adrcheck/cli.py` uses it and makes one judge call. `action.yml` passes `--as-one`
always: a pull request is judged as what it merges. Commit-by-commit judging stays the default for the CLI
without `--as-one`, because a sweep over history needs the per-commit verdicts to find the commit where a
decision was overtaken.

## Consequences

One judge call per pull request however many commits it has, so `max-calls` matters only for per-commit
sweeps. A conflict introduced and repaired inside one pull request is invisible to the gate, which is the
point; it stays visible to a per-commit sweep later. The comment names the pull request's head commit and
the first commit's subject. The parent probes run against the merge base, so "already present at the
parent" means present on the base branch, which is the right question for a merge.
