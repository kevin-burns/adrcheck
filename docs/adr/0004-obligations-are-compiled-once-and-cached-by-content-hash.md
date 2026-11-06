# 4. Obligations are compiled once per ADR and cached by content hash and prompt version

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/adapters/obligation_cache.py, src/adrcheck/adapters/claude_judge.py, src/adrcheck/ports.py

## Context

Reading an ADR with a model costs money and time. The ADR changes rarely; the code changes
constantly. Checking a diff against the raw ADR text on every run pays the reading cost every
time and lets the reading drift between runs.

## Decision

An ADR is compiled into obligations by an `ObligationCompiler` once. `CachedCompiler` stores the
result under a key derived from the ADR's content hash and `PROMPT_VERSION`, and returns the
cached obligations on every later run until either changes. The judge sees compiled obligations,
not the ADR prose. Changing the compile prompt requires bumping `PROMPT_VERSION`, which
invalidates every cached compile.

## Consequences

Steady-state cost is the judge calls only. Two runs on the same ADR text and prompt version
produce identical obligations. The cache directory is safe to commit or share between CI and
developers.
