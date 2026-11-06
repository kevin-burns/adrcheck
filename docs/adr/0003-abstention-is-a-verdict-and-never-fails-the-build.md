# 3. Abstention is a verdict and never fails the build

Date: 2026-11-06
Status: Accepted
Bead: claude-skills-ol5w
Applies to: src/adrcheck/domain/verdict.py, src/adrcheck/usecases/check.py, src/adrcheck/cli.py

## Context

Most changes do not settle whether a decision is honoured. Forcing a yes or no there produces
false alarms, and false alarms are what gets a checker uninstalled.

## Decision

`Verdict` has four values: CONFLICT, COMPLIANT, UNCLEAR and ADR-OVERTAKEN. UNCLEAR is a
first-class result, reported with its reason. A judge that errors, times out or returns
unparseable output yields an UNCLEAR finding whose reason begins `judge error`; it never yields
COMPLIANT. Only CONFLICT can make `adrcheck check` exit non-zero under `--fail-on conflict`.

## Consequences

An unreachable model cannot turn a build green by accident, and cannot turn it red either. The
report must show UNCLEAR counts so a run that abstained on everything is visible as such.
A separate exit code for "could not evaluate" is tracked in bead adrcheck-yi8.
