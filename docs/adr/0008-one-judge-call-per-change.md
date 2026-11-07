# 8. The judge sees every selected ADR of a change in one call

Date: 2026-11-07
Status: Accepted
Bead: adrcheck-c6l.1
Applies to: src/adrcheck/ports.py, src/adrcheck/usecases/check.py, src/adrcheck/adapters/claude_judge.py

## Context

The first dogfood run sent one judge call per selected ADR. A lint commit that touched `check.py`,
which six ADRs name, cost seven calls and about two dollars, because the same hundred-thousand-token
diff travelled seven times. Separate `claude -p` sessions cannot share a cached prefix, so the diff
is the cost and the number of calls is the multiplier. The use case was deciding call granularity,
which is a mechanism of the adapter, not a rule of the application.

## Decision

`ChangeJudge.judge()` in `src/adrcheck/ports.py` takes a `Change`, every `JudgeCase` selected for
it and one `Context`, and returns one `JudgeResponse` for all of them. The use case in
`src/adrcheck/usecases/check.py` calls the judge at most once per change. The adapter owns how many
model calls that becomes; `ClaudeJudge` in `src/adrcheck/adapters/claude_judge.py` makes one. The
response carries `not_relevant`, the ADR numbers the judge dismissed, and findings keyed by
obligation id. A finding whose obligation id names an ADR that was not asked about is recorded as a
problem on the report, never as a verdict.

## Consequences

The diff and the post-images are sent once per change. The measured cost of the lint commit fell
from $2.00 to $0.31 and the three UNCLEAR reflow rows did not recur. The judge may return one
finding per ADR rather than one per touched obligation; whether that hides a conflict behind a
compliant sibling is checked against the planted-conflict corpus in bead adrcheck-2nj. When the
selected ADRs make one prompt too long, the adapter must split into several calls without the use
case noticing; that split is not implemented yet.
