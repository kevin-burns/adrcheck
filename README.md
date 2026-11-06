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

Status: pre-release. A one-day spike is measuring it on a real repository before any of this
is promised. See `docs/design.md` for the module boundaries and `docs/spikes/` for results.

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
