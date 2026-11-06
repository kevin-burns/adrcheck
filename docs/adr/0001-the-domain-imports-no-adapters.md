# 1. The domain imports no adapters, use cases, CLI or I/O libraries

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/domain/**, src/adrcheck/ports.py

## Context

adrcheck follows the dependency rule from Clean Architecture: policy does not depend on detail.
The judge is a subprocess today and an HTTP call tomorrow; git is one change source and a unified
diff on stdin is another. The rules about verdicts, verification, selection and hygiene must not
know which.

## Decision

Modules under `src/adrcheck/domain/` import only the standard library and each other. They never
import `adrcheck.adapters`, `adrcheck.usecases`, `adrcheck.cli`, `subprocess`, `requests` or
`httpx`. Every dependency the domain or use cases need from the outside world is a `Protocol` in
`src/adrcheck/ports.py`: `AdrSource`, `ChangeSource`, `RepoReader`, `ObligationCompiler`,
`ChangeJudge`.

## Consequences

The domain builds and tests with no network, no git and no model. The boundary is enforced by
`tests/test_boundaries.py`, which fails on the first offending import. A new provider is a new
adapter and never a domain change.
