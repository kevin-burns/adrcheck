# Contributing

adrcheck is small and its rules are deliberate. Most of what follows exists so that a change to a verdict
is a decision someone made, not something that drifted in.

## Before a pull request

Open an issue first for anything that changes a verdict, a probe, selection, verification or a prompt.
Those are recorded as ADRs under `docs/adr/`, and adrcheck checks its own pull requests against them. A
pull request that contradicts an ADR gets a CONFLICT comment from the tool itself; the right fix is a
superseding ADR in the same pull request, or an `Adr-Exception:` trailer with a reason.

Drive-by pull requests that touch many files, rename things, or "modernise" without an issue are closed
without review.

## Pull requests written with AI assistance

Say so. The pull request template has three boxes, none, assisted, generated; tick exactly one. The
hygiene check fails a pull request with none ticked. Ticking "generated" is not a mark against the change,
and leaving it unticked is.

Whatever you tick, you are the author. You have read every line, run the tests and, for a rule change, the
eval set, and you can explain the change in review. A pull request whose description cannot be defended
by its author is closed.

Commits carry no AI attribution or session trailers. The `commit-msg` hook rejects them.

## Evidence

- `uv run pytest -q` green, and new tests for new behaviour. The domain is test-first; the deterministic
  modules were written that way and stay that way.
- For a rule or prompt change, the frozen corpora: `evals/cases/adrcheck.json` and
  `evals/cases/planted.json` (build the planted repository with `evals/planted/build.py`). Paste the score
  lines in the pull request. A change that moves a corpus off full marks needs the reason written down.
- `prek run --all-files` passes: ruff, bandit, markdownlint, yamllint, gitleaks, the test suite, and the
  Conventional Commits check.

## What never goes in

- Personal or client data. Fixtures are synthetic or from this repository. The job-search corpus is
  private and is referenced by an environment variable, never bundled.
- Secrets or their values, in code, fixtures, spikes or commit messages. Reference them by variable
  name.
- Code from a project under a non-permissive licence. Ideas are credited in the README's prior-art
  section; code is not copied. Read the licence before reading the source.

## Dependencies and actions

Dependabot keeps `pyproject.toml`, `.pre-commit-config.yaml` and the GitHub Actions current, weekly,
grouped by ecosystem, majors one at a time. Actions are pinned to commit SHAs with the version in a
comment; keep that shape when adding one.

## Commits

Conventional Commits, enforced by the hook: `feat`, `fix`, `docs`, `ci`, `chore`, `perf`, `refactor`,
`test`, with an optional scope. The body says why, not what; the diff says what.
