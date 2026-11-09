# Pull request

## Summary

<!-- One paragraph: what changes and why. Link the bead or issue if there is one. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Rule change: a verdict, a probe, selection or verification behaves differently (name the ADR)
- [ ] Documentation only
- [ ] Refactor or chore, no behaviour change
- [ ] Dependency update

## Touch area

- [ ] Domain (`src/adrcheck/domain/`): verdicts, verify, select, overtaken, lint
- [ ] Use cases (`src/adrcheck/usecases/`)
- [ ] Adapters (`src/adrcheck/adapters/`): git, markdown, providers, render
- [ ] Prompts (`src/adrcheck/chatmodel/`): bumps `PROMPT_VERSION`, recompiles every cached ADR
- [ ] Action or workflows (`action.yml`, `.github/`)
- [ ] ADRs (`docs/adr/`) and their compiled cache (`.adrcheck/obligations/`)
- [ ] Docs, evals, spikes

## Test plan

<!-- How you verified it. Paste the command and its last line. A rule change also needs the eval set: -->

```sh
uv run pytest -q
adrcheck eval --cases evals/cases/adrcheck.json --run --report /tmp/a.json
adrcheck eval --cases evals/cases/planted.json --run --report /tmp/p.json   # needs ADRCHECK_EVAL_PLANTED_REPO
```

## AI assistance

Tick exactly one. A pull request with none ticked fails the hygiene check.

- [ ] None: written and tested by hand
- [ ] Assisted: a model drafted or reviewed parts; every line was read, run and understood by the author
- [ ] Generated: substantially model-written; the author has run the tests and the eval set and vouches for it

<!-- Whichever you tick, the commits carry no AI attribution or session trailers; the commit-msg hook rejects them. -->

## Checklist

- [ ] Tests added or changed for the behaviour (or N/A, say why)
- [ ] `prek run --all-files` passes locally
- [ ] No personal or client data: no real names, hosts, keys, or private repository content in fixtures or spikes
- [ ] Docs updated where behaviour or a flag changed
- [ ] Prior art credited if an idea came from another project; no code copied from a non-permissive licence
