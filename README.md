# adrcheck

Checks code changes against a team's architecture decision records (ADRs), in both directions,
and publishes its own false-alarm rate.

- A commit that breaks an accepted ADR is reported as CONFLICT, with the changed line, the
  ADR quote it contradicts, and a one-sentence reason. Every quote is verified against the
  ADR, every line against the diff, before you see it.
- An ADR the code has already moved past is reported as ADR-OVERTAKEN, with a draft
  superseding ADR, instead of flagging the code.
- Anything the evidence does not settle is UNCLEAR. Abstaining is a verdict, not a miss.

Advisory by default. Structured JSON out, so a caller can gate if it wants to.

Status: pre-release. Measured on two repositories so far; the numbers and the labelled rows are in
`docs/spikes/` and `evals/cases/`. See `docs/design.md` for the module boundaries and `docs/adr/` for
the decisions adrcheck holds itself to (it checks its own pull requests against them).

## Quickstart

ADRs live in the repository as numbered markdown files, in any of the common shapes (Nygard, MADR,
Y-statements, Tyree and Akerman, bold labels, a table). adrcheck binds on the role of a section, not
its heading: the decision and its consequences bind, the context explains, the considered options
never bind.

```bash
# run from a clone, no install
uvx --from git+https://github.com/kevin-burns/adrcheck adrcheck --help

# hygiene of the ADR set, no model
adrcheck lint --adr-dir docs/adr

# compile ADRs into obligations once; cached under .adrcheck/obligations, safe to commit
adrcheck compile --adr-dir docs/adr

# judge the commits on a branch; exit 2 on a verified CONFLICT, 3 when nothing could be evaluated
adrcheck check --adr-dir docs/adr --range origin/main..HEAD --format md --fail-on conflict
```

The model is chosen with `--model provider:model`. `anthropic:claude-sonnet-5-5` uses the Anthropic
API and needs `ANTHROPIC_API_KEY` in the environment; `claude-cli:sonnet` uses a logged-in Claude Code
install and needs no key. `openai:<model>` posts to any OpenAI-compatible endpoint, `OPENAI_BASE_URL`
and `OPENAI_API_KEY` from the environment; `ollama:<model>` is the same against `OLLAMA_HOST`, default
`http://localhost:11434`. Those two report a cost of zero because no price table fits every endpoint.
A commit that touches nothing an ADR governs costs no model call. A commit that does costs one call,
about 100k input tokens; measured runs are in `docs/spikes/`. `--compile-model` puts the compile seat on
a different provider, for example a local model for the once-per-ADR compile and Sonnet for the judge.
The obligation cache is keyed by ADR text and prompt version, not by model: delete `.adrcheck/obligations`
to recompile after changing the compile model.

Waive an ADR for one commit with a trailer that carries a reason:

```text
Adr-Exception: ADR-3 migration script, reverted in the next commit
```

### Adopting on a repository with history

The first run lists every accepted ADR whose named anchors are no longer in the tree. Review that list
once and keep it:

```bash
adrcheck check --adr-dir docs/adr --commit HEAD --write-baseline   # writes .adrcheck/baseline.json
```

Commit the file. Later runs count the rows it names and list only new ones. Nothing rewrites it except
another `--write-baseline`; edit it like source when an ADR is retired or an anchor is renamed.

ADRs that cannot carry an `Applies to` line can be scoped from the repository instead:

```toml
# .adrcheck/map.toml
[[adr]]
id = 4
paths = ["enrich/**", "cli.py"]
```

The header wins where both exist, and `adrcheck lint` reports the disagreement.

### In a pull request

```yaml
# .github/workflows/adrcheck.yml
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  adrcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7.0.1
        with:
          fetch-depth: 0
      - uses: kevin-burns/adrcheck@main
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        with:
          adr-dir: docs/adr
```

The action posts one comment with the report and updates it on every push. A verified CONFLICT fails
the step. "Could not evaluate" (no key, provider down) is a warning, not a failure: an unreachable
model is not a finding.

### Verdicts

| Verdict | Meaning | Exit code |
|---|---|---|
| CONFLICT | a changed line contradicts a quoted sentence of the ADR's decision; both verified | 2 with `--fail-on conflict` |
| COMPLIANT | the change touches the ADR's ground and keeps to it | 0 |
| UNCLEAR | the diff does not settle it; the reason is shown | 0 |
| ADR-OVERTAKEN | the contradiction already existed at the parent commit; the ADR, not the change, is stale | 0 |

## Prior art and credit

- Michael Nygard, "Documenting Architecture Decisions" (2011), the ADR format.
- Neal Ford, Rebecca Parsons and Patrick Kua, *Building Evolutionary Architectures*
  (O'Reilly, 2017), architectural fitness functions.
- David Boyne's EventCatalog ADR compliance workflow (blog post "Turn your ADRs into automated
  checks", 2026-11-05) demonstrated checking pull requests against ADRs and verifying the quote
  and the changed line. adrcheck is built from that idea, not from its source, which is under the
  Business Source License.
- ruflo-adr (ruvnet/ruflo, MIT): ADR id references in code as a scoping signal, and the ADR
  graph hygiene checks.
- zircote/adr (MIT): front-matter-first selection with stated exclusions, and the
  "what not to flag" list.
- MADR, Markdown Any Decision Records (adr.github.io/madr, MIT or CC0): the "Confirmation" section is the natural home for compiled obligations.
- The architecture-decision-record template collection by Joel Parker Henderson (the collection's own text is CC BY-NC-SA 4.0; each template keeps its original author's licence): the catalogue adrcheck's role map is built from. adrcheck maps template section names to roles and copies no template text.
- Two unrelated projects are called ADR Guard. (1) chohan-sarmad-ali/delivery-gates (MIT): a GitHub Action that fails a PR when watched paths change without an ADR being added or updated, with an `ADR-Exempt:` trailer, plus a duplicate-number gate. (2) rodri-oliveira-dev/adr-guard (MIT, .NET): an ADR toolkit that validates structure, status, links and supersession (codes ADR001-ADR014), correlates git changes with an explicit ADR-to-code map (`impact`), verifies narrow fitness rules against effective ADRs with "unknown is never pass" semantics and reviewable baselines (`drift`), and reviews an ADR's text with a model (`review`). Neither reads the code to judge whether a change complies with a decision; that is adrcheck's job, and it composes with both. adrcheck borrows from (2) the explicit outcome vocabulary pass / violation / unknown / not-applicable, the distinct exit code for "could not evaluate", and baselines reviewed like source.

## Licence

Apache-2.0.
