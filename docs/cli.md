# Command reference

Five subcommands. `adrcheck <command> --help` prints the same flags; this page says what each is for and
which pages explain it. Flags shared by several commands are listed once.

| Command | What it does | Needs a model |
|---|---|---|
| `check` | judge commits against the accepted ADRs, both directions | yes, except `--tier free` |
| `lint` | hygiene of the ADR set: numbers, statuses, references, links | no |
| `compile` | compile ADRs into obligations and cache them | yes |
| `explain` | one ADR's obligations and where each anchor lives in the code | no |
| `eval` | score a saved report against frozen cases | no, unless `--run` |

## Exit codes

| Code | `check` | `lint` | `compile` | `explain` | `eval` |
|---|---|---|---|---|---|
| 0 | no CONFLICT, or none with `--fail-on`; also nothing staged | clean | compiled | printed | every case hit |
| 1 | no ADR directory found | issues found, or no ADR directory | no ADR directory | no such ADR, or no ADR directory | at least one miss |
| 2 | a verified CONFLICT with `--fail-on conflict`; a usage error from the parser | | | | |
| 3 | could not evaluate | | model unreachable | compile failed | could not run |

Exit 3 is a warning in the Action and the GitLab job: an unreachable model is not a finding (ADR-3).

## Shared flags

| Flag | Default | Meaning |
|---|---|---|
| `--adr-dir DIR` | the first of `docs/adr`, `docs/decisions`, `docs/architecture/decisions`, `doc/adr`, `doc/architecture/decisions`, `adr`, `adrs`, `decisions` that exists | directory of ADR markdown files (ADR-12: every `.md` there is a record except README, index and template) |
| `--repo PATH` | `.` | git repository root |
| `--map PATH` | `.adrcheck/map.toml` | repo-side scope map: which paths an ADR applies to, for records with no `Applies to` line; see [writing-adrs.md](writing-adrs.md) |
| `--model provider:model` | `anthropic:claude-sonnet-5-5` when the Anthropic key variable is set, else `claude-cli:sonnet` | the judge and, unless overridden, the compiler; providers in [providers.md](providers.md) |
| `--compile-model provider:model` | same as `--model` | the compile seat only; obligations are cached, so a local model here costs nothing at judge time |

`lint` takes the first three; `explain` and `compile` take all five; `eval` takes the two model flags.

## check

What to judge, exactly one of:

| Flag | Meaning |
|---|---|
| `--range A..B` | a git revision range, one judge call per commit, or one call for the whole range with `--as-one` |
| `--commit SHA` | one commit |
| `--staged` | the index, as a pre-commit hook sees it; reads the commit message being written for an `Adr-Exception` trailer |

How to judge:

| Flag | Default | Meaning |
|---|---|---|
| `--tier free\|judge` | `free` with `--staged`, else `judge` | free: no model, no key; forbidden patterns on added lines from the cached compile, and the stale sweep. judge: the model |
| `--as-one` | off | judge `--range` as the one change it merges: net diff, every commit message, one judge call (ADR-13). The Action and the GitLab job always use it |
| `--max-calls N` | no cap | judge at most N commits this run; later commits are reported as not judged, never silently green |
| `--baseline PATH` | `.adrcheck/baseline.json` | reviewed stale rows; rows named here are counted, not listed |
| `--write-baseline` | off | record this run's stale list to `--baseline`; review the diff like source |

What to print:

| Flag | Default | Meaning |
|---|---|---|
| `--format json\|md\|codequality` | `json` | json: the full report; md: the comment; codequality: GitLab Code Quality JSON |
| `--codequality PATH` | none | also write the findings as Code Quality JSON to PATH, whatever `--format` prints |
| `--fail-on conflict` | off | exit 2 when any CONFLICT is reported |

The verdicts and every report line are defined in [verdicts.md](verdicts.md); the Action and the GitLab
job in [ci.md](ci.md).

## lint

No further flags. Prints one line per finding, `ADR-N code: detail`, and exits 1 if there is any. The codes
are listed in [verdicts.md](verdicts.md#hygiene-codes).

## compile

| Flag | Meaning |
|---|---|
| `--prune` | delete cache entries that no current ADR produces, such as those of a record since rewritten or removed |

The cache lives under `.adrcheck/obligations/`, keyed by a hash of the ADR text and the prompt version, and
is meant to be committed so CI never recompiles. A changed ADR gets a new entry; `--prune` removes the old
one.

## explain

| Flag | Meaning |
|---|---|
| `--adr N` | the ADR number, required |
| `--at REF` | the revision to look in, default `HEAD`; use a tag or an old commit to see what the ADR bound to then |

Prints each obligation with its anchors, the files that contain each anchor and how often, and marks an
anchor STALE when nothing in the tree carries it. No judge call; the compile cache must hold the ADR.

## eval

| Flag | Meaning |
|---|---|
| `--cases PATH` | `evals/cases/<corpus>.json`, required |
| `--report PATH` | a `check --format json` report to score, required; written when `--run` |
| `--run` | run `check` over the corpus commits first, then score |
| `--model`, `--compile-model` | as for `check`, used only with `--run` |

Scores hit, quiet, miss and absent per case and exits 1 on any miss. The corpora shipped with adrcheck and
their numbers are in the README under "What it has found so far".
