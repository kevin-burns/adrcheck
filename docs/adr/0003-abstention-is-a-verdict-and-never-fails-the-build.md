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
COMPLIANT. Only CONFLICT can make `adrcheck check` exit 2 under `--fail-on conflict`. A run in which the
judge was called and no case received any verdict, or in which an ADR could not be compiled because the
provider failed, exits 3: that names an operational failure, not a finding, and a pipeline decides for
itself whether to treat it as a stop.

## Consequences

An unreachable model cannot turn a build green by accident, and cannot mark a conflict either: exit 3 is
distinct from exit 2 so a pipeline can tell "the checker could not run" from "the checker found a
problem". A partial failure, where some cases got a verdict and others a judge error, still exits 0 or 2
and shows the errors as UNCLEAR rows. The report must show UNCLEAR counts so a run that abstained on
everything is visible as such. Amended 2026-11-08 under bead adrcheck-yi8.
