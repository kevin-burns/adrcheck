# adrcheck design

adrcheck checks code changes against a team's architecture decision records
(ADRs), in both directions: a change that breaks an accepted decision, and a decision the code
has quietly overtaken. It is advisory, measured, and publishes its own false-alarm rate.

The decisions behind this layout are the ADRs under `docs/adr/`; the frontier session that produced the
first of them (2026-11-06) is in a private tracker. This file records the module boundaries and why.

## Bounded context and language

One context: decision compliance. Terms, used the same way in code, tests and reports:

| Term | Meaning |
|---|---|
| ADR | One decision record, parsed from markdown in any of the common shapes (Nygard, MADR, Y-statement, tables, bold labels). Has a Status and sections. |
| Obligation | One MUST or MUST NOT compiled from an ADR, with the quote it derives from and a checkability class (mechanical, structural, intent, process). |
| Change | One commit (or staged diff): per file, the lines added and removed. |
| Selection | The ADRs that apply to a change, with the signals that fired (glob, id reference, model). |
| Finding | The judge's claim about one (change, obligation) pair: a verdict, an evidence line, a quote, a one-sentence contradiction. |
| Verdict | CONFLICT, COMPLIANT, UNCLEAR or ADR-OVERTAKEN. |
| Exception | A git trailer `Adr-Exception: ADR-NNNN <reason>` that waives one ADR for one change. |
| Hygiene issue | A structural fault in the ADR set: dangling supersede reference, cycle, status mismatch, missing Status. |

## Layout and the dependency rule

```text
src/adrcheck/
  domain/      pure: ADR, Obligation, Change, Finding, verify rules, selection by glob and id,
               CONFLICT-vs-OVERTAKEN rule, hygiene lint, exception parsing. Imports nothing
               from adapters, subprocess, or the network.
  ports.py     Protocols the use cases need: AdrSource, ChangeSource, RepoReader, ObligationCompiler,
               ChangeJudge; the judge's request and reply types; NotCompiled.
  chatmodel/   prompts and reply parsers, provider-neutral (ADR-9).
  usecases/    check (select, compile, judge, verify, classify, stale sweep), explain, mechanical
               (the free tier's judge), evaluate. Orchestrate ports and domain; hold no I/O.
  adapters/    markdown ADR parser and source, scope map, baseline file, git change source and repo
               reader, chat runners (claude -p, Anthropic SDK, OpenAI-compatible), file-backed
               obligation cache, JSON and markdown renderers, provider lookup.
  cli.py       composition root: parses flags, wires adapters to use cases.
```

Dependencies point inward: `cli -> adapters -> usecases -> domain`, and `adapters -> ports`.
A test asserts that nothing under `domain/` imports from `adapters/`, `subprocess`, or `cli`.

## Design rules applied

- **Clean Architecture.** The model, git, the filesystem and the renderers are details behind
  ports owned by the inner layers. The judge is the most volatile piece and the one we most want
  to swap (sonnet now, SDK later, local model maybe), so it sits furthest out. Core tests run
  without git or a model.
- **Role-sized interfaces.** `ObligationCompiler` and `ChangeJudge` are separate Protocols even
  though one adapter implements both; a cached compiler and a live judge are different roles.
- **Deep modules.** `verify()` is one function hiding three rules (line in change, quote in ADR,
  quote from Decision or Consequences). The ADR parser hides two formats behind one `Adr`.
  Callers never learn which format or which rule.
- **DDD distilled.** Judgement (compile, select, judge, verify, overtaken rule) is the Core
  Domain and gets the modelling effort. Parsing and git are Supporting. CLI and rendering are
  Generic. "Status", "Decision" and "Consequences" keep the ADR community's meaning.
- **Pragmatic Programmer.** The verdict semantics have one owner (`domain/verdict.py`). The
  judge prompt and the spike runner are the prototype parts and are named as such; the
  deterministic modules are built test-first and kept.

## Rules knowingly bent

- The domain boundary is enforced by package structure and an import test, not a separate
  distribution. The lightest enforceable boundary is enough at this size.
- `AdrSource` exists for one implementation (markdown). It is kept because the second
  (Ogham) is a settled decision, and the Protocol has one method.
- The obligation cache key (ADR content hash plus prompt version) is a policy decision that
  lives in the use case, while the storage lives in an adapter. Two places know about the key;
  the use case owns its meaning.

## Rules learned from the first compile (2026-11-06, before the commit run)

Both came from reading the compiled obligations of the four job-search ADRs, not from the run.

- **An anchor the ADR does not name is the compiler's invention.** Sonnet proposed `mandates`
  such as `fold_count` and `time.sleep` that appear nowhere in the ADR. Absence of an invented
  anchor must never make an ADR look overtaken, so `parse_compile_reply` keeps only mandates
  that occur verbatim in the ADR text, and the parent probe requires *all* of them present.
  A generic token (`get`) can then not rescue a missing specific one (`import_rows`).
- **The precedent probe uses the judge's cited line, not compiler patterns.** The compiler's
  `forbids` were over-broad (`hashlib.`, `.filter(`) and would have turned every real CONFLICT
  into ADR-OVERTAKEN, since store.py itself uses hashlib. "Already violated at the parent" is
  now asked as: did this exact changed line already exist somewhere at the parent? Precise,
  free, and wrong only in the safe direction (a variant line stays CONFLICT). `forbids` are
  still compiled and reported, for a human to read.

## Rules learned from the first run (2026-11-06, see docs/spikes/2026-11-06-job-search.md)

- **Stale detection is a per-run sweep, not a per-diff verdict.** `stale_sweep` probes every
  accepted ADR's named anchors in the code at the end of the range. A stale ADR's files may
  never be touched again, so selection by diff can never reach it. Q14's classification still
  applies to individual findings; the sweep is the second leg.
- **Presence means presence in code.** `GitRepo.contains` blanks Python comments and
  docstrings, skips prose files, and includes file paths, so "import_rows was removed" in a
  docstring does not keep ADR-4 alive and an ADR that names `enrich/linkedin.py` is probed
  against the tree.
- **verify() compares lines after stripping indentation**, tolerating a copied `+` or `-` marker
  only when the bare line does not match. Models drop indentation when they copy.
- **A removed line is never a precedent.** The "already violated at the parent" probe asks only
  about added lines.

## Rule learned from the portability question (2026-11-06)

**Model roles, not model tiers.** adrcheck has two model seats today, compiler and judge, and a third,
the gate, planned under bead c6l. Each is a
role bound to a `provider:model` string in config. Claude is one provider; an OpenAI-compatible
HTTP endpoint (OpenAI, Ollama, vLLM, LM Studio, Qwen, Granite) is another. Prompts and reply
parsers are policy and belong outside any provider adapter, so every provider sends the same
prompt and the eval set compares models rather than prompt variants.

The property that makes this safe: verify() and the stale sweep are deterministic and model-free.
A weaker judge fails verification more often and so degrades to UNCLEAR, not to false CONFLICT.
Mechanical obligations need no model at all. How far the property holds per model is measured on
the eval set (beads adrcheck-2kh and the provider bead), never assumed.

**Two model interfaces, not one.** A chat model takes a prompt and returns text; a decision model
(TypeSafe Jev and its kind) takes a state and bounded questions and returns typed answers with
calibrated probabilities. They are different ports. The judge must be a chat model because a
CONFLICT needs a quoted line that verify() can check, and a decision model cannot quote. The gate,
checkability tagging and post-judge confidence are bounded questions over evidence already
gathered, so they are classifier seats and a decision model can fill them. Rule from the Jev
write-up (research/adr-checker/jev.md): a classifier fails when the state does not contain the
evidence, so feed it the compiled obligations and the relevant hunks, never the whole diff.

## Rules learned from the format question (2026-11-06)

**Bind on roles, not headings.** Templates differ (Nygard, MADR, Y-statements, Tyree & Akerman,
Confluence's Decision blueprint, a dozen more), but every one carries the same four roles:
binding, intent, rejected, process. The parser maps headings to roles through a catalogue and a
per-repo override, and says "no <role> found" rather than guessing. The acceptance test is one
decision written in every template compiling to the same obligations.

**The Confirmation section is the contract.** MADR 4 already has a "Confirmation" section whose
stated purpose is how compliance will be confirmed. Compiled obligations belong there, edited and
confirmed by the author. An author-confirmed obligation settles letter-versus-intent at write time,
needs no model at check time, and is the only form the checker should ever treat as certain.

**Letter and intent are both reported, never merged.** An obligation carries its binding sentence
and its driver. A finding that breaks the letter while meeting the stated intent is `letter_only`,
shown as such, and warns by default. Planned under bead git, not yet built. The checker does not decide
which one the author meant.
