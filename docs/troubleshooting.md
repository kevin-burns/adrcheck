# Troubleshooting

Each entry is a message you can see, or a report line that looks wrong, and what to do about it. Messages
go to stderr; the report goes to stdout.

## Messages

**`no ADR directory found; pass --adr-dir`** (exit 1). adrcheck tried `docs/adr`, `docs/decisions`,
`docs/architecture/decisions`, `doc/adr`, `adr` and `decisions` under `--repo` and found none. Pass
`--adr-dir`. In the Action, the `adr-dir` input defaults to `docs/adr` and nothing is discovered.

**`could not evaluate: ...`** (exit 3). The run could not produce verdicts. The text after the colon is the
reason: a missing key, a connection refused, an HTTP error with the endpoint's own message. Nothing about
your code was judged. In the Action this is a warning, not a failed step. In a shell or a hook it is exit 3
like any other non-zero exit.

**`could not evaluate: every judge call failed; see the judge error notes`** (exit 3). Every commit that
needed a judge got an error back. Each selected ADR on those commits reads UNCLEAR with `judge error: ...`
as its note. Usually a provider outage or a model name the endpoint does not know.

**`could not compile ADR-N: ...`** (exit 3). The compile seat failed on that ADR. With Ollama the message is
often memory: `model requires 17.5 GiB but only 17.3 GiB are available`. Pick a smaller model for
`--compile-model`, or compile on a machine that has the room and commit the cache.

**`nothing staged`** (exit 0). `--staged` found an empty index. Stage something or use `--commit`.

**`set ADRCHECK_EVAL_X_REPO to the path of the X repository`**. An eval corpus names its repository by
environment variable because the repository itself is not bundled. Export it and rerun.

**`N change(s) not judged: --max-calls N reached`**. The call cap did its job. Those commits read UNCLEAR
with `not judged: call budget of N reached`. Raise the cap or check a shorter range.

**`model cost this run: $0.0000 (cached ADRs cost nothing)`** after `compile`. Not an error. Every ADR was
already in `.adrcheck/obligations/` under its current text.

## Report lines that look wrong

**A CONFLICT I disagree with.** Read the quote. If the sentence it cites is not in the Decision or
Consequences section, or not in the ADR at all, that is a bug: verification should have caught it, and a
copy of the report is a good issue. If the sentence is there and binding, the disagreement is with the ADR,
and the options are on the [workflow page](workflow.md#what-a-conflict-asks-of-you).

**UNCLEAR with `line-not-in-change`.** The judge cited a line the diff does not add or remove. Common on
`--staged` when the file is partly staged, or when the judge quoted a context line. It is not a verdict on
your code; the claim was dropped because it could not be checked.

**UNCLEAR with `quote-outside-decision`.** The judge quoted the Context or Options section. Those never
bind. If the ADR's Decision is under an unusual heading, the parser may not have recognised it; run `lint`
and compare the heading against the names on the [writing ADRs page](writing-adrs.md).

**ADR-OVERTAKEN on a commit that did nothing wrong.** That is what the verdict says: the contradiction was
already there at the parent, and the note names which probe showed it. The ADR, not the commit, needs
attention. If the note is `removed anchor X had no callers at parent`, the commit deleted dead code the ADR
still names.

**A stale row for something that exists.** The stale sweep searches code only. It skips markdown, text,
HTML, images and lock files, and for Python it blanks comments and docstrings before searching. Two gaps:

- A name that appears only in a comment or docstring of a non-Python file counts as present, because only
  Python prose is stripped.
- A name that appears only in a JSON, YAML or TOML file counts as present, because those are read as code
  by the sweep. If the ADR's anchor is a config key, this is what you want; if the anchor is a function
  that only a config file still mentions, the row will not appear until the config changes.

The other direction is rarer: an anchor mentioned in a `.txt` or `.md` file only is reported missing. Name
code, not documents, in the Decision section. Files under `.adrcheck/` are never read as code, so the
committed obligation cache cannot satisfy its own anchors.

**`uncovered files` is high.** The count is changed files none of the judged ADRs' globs matched. On a big
refactor it is often most of the diff and means nothing. On an ordinary change it means your `Applies to`
globs are narrower than the code the decisions actually govern.

**The judge was shown an ADR that has nothing to do with the change.** It has no `Applies to` header, so
nothing says it does not apply, and it is sent on every commit. Add the header or a `.adrcheck/map.toml`
row; see the [writing ADRs page](writing-adrs.md#the-header-lines-adrcheck-reads).

**Two obligations of one ADR disagree about one line.** Both become UNCLEAR and the note names the pair. The
ADR probably says the same thing twice in slightly different words; compile output shows the two
obligations. Tighten the record.

## Costs that surprised you

- Input tokens through `claude-cli:` run far higher than the same prompts through the API: on the planted
  corpus, about 51,000 a call against 1,500. The difference is the CLI's own system prompt, about 45,000
  tokens on every call, measured with a two-token prompt in [the CLI-route spike](spikes/2026-11-09-cli-route.md).
  Compare tokens within one route only, and expect the CLI route to judge more cautiously as well.
- A range check is one call per commit that touches governed paths. Count before you run; `--max-calls`
  bounds it.
- The first `check` on a repository with no committed `.adrcheck/obligations/` compiles every selected ADR.
  Run `compile` once and commit the directory.
