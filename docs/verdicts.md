# What the verdicts mean

A report has three kinds of line: verdicts on findings, notes about ADRs that were not judged, and the
stale list. This page defines each, then the hygiene codes `lint` prints, then the exit codes.

## The four verdicts

Each finding is one obligation of one ADR held against one changed line.

### CONFLICT

The change contradicts a sentence in the ADR's Decision or Consequences section, and adrcheck has
verified the claim before showing it to you. Verified means three things checked without a model: the
cited line is in the diff, the quote is in the ADR verbatim, and the quote comes from a binding section.
A judge claim that fails any of those is shown as UNCLEAR with the failure named, never as a CONFLICT.

CONFLICT is the only verdict that can fail a build, and only when you ask with `--fail-on conflict`.

What to do: one of three things, and the report should make clear which. Fix the code. Change the
decision, by superseding the ADR. Or declare the exception in the commit message:

```text
Adr-Exception: ADR-4 one-off backfill of the November export; the importer returns in the next commit
```

A trailer with a reason waives that ADR for that commit and is reported as COMPLIANT with the reason
shown. A trailer without a reason waives nothing and is reported as a problem.

### COMPLIANT

The change touches the ground the ADR governs and keeps to the decision. The finding shows which
obligation was in play and why the judge was satisfied. A waived ADR also appears as COMPLIANT, with the
waiver's reason as its note, so an exception is visible in the report and in git history.

### UNCLEAR

The diff does not settle the question, and the reason says why. Four sources:

- The judge said so. Often an `intent` obligation, where the behaviour the ADR cares about is not visible
  in a diff.
- A CONFLICT claim failed verification. The note names the failure: `line-not-in-change`,
  `quote-not-in-adr`, `quote-outside-decision`, or `unknown-obligation` when the judge cited an obligation
  id the ADR does not have.
- The judge call failed for that commit. One UNCLEAR per selected ADR, note `judge error: ...`, so a
  provider fault is visible per commit and is never a CONFLICT or a silent pass.
- The judge contradicted itself: two obligations of the same ADR gave CONFLICT and COMPLIANT on the same
  line. Both become UNCLEAR and the note names the pair.

UNCLEAR never fails a build. Read it as a review comment, not a result.

### ADR-OVERTAKEN

The judge found a contradiction, but adrcheck can show it already existed before this change. The
author did not break the decision; the code had already left it behind, and the ADR is what needs
attention. Three probes against the parent commit establish this:

- an anchor the obligation mandates was already absent;
- the cited line already existed elsewhere in the code;
- the cited line removes a name that nothing but its own definition referenced, so the change deletes
  dead code.

The note says which. ADR-OVERTAKEN never fails a build. The first two probes apply only to a CONFLICT. The
third also settles an UNCLEAR about a removed line, because a judge that sees only the diff cannot know
whether a deleted name had callers and the count can. A COMPLIANT verdict is never changed by a probe.

## Lines that are not verdicts

| Line | Meaning |
|---|---|
| `judged, not relevant: ADR-2, ADR-5` | these ADRs were shown to the judge because the change touched their paths or mentioned their number, and the judge set them aside |
| `proposed, not enforced, touches its paths: ADR-12` | a Proposed ADR governs a path this change touched; nothing is enforced until it is Accepted, but you should know |
| `uncovered files: 4` | changed files that none of the judged ADRs' `Applies to` globs matched; a large number on a large change means your globs are narrower than your code |
| `problem: ...` | something the judge or the commit message got wrong, for example an exception trailer with no reason |
| `_No ADR applied to this change._` | nothing in this commit touched an accepted ADR's ground; no model call was made |

Only Accepted ADRs are enforced. Proposed, Deprecated, Superseded and Rejected ADRs are excluded, and the
JSON report records the reason for each exclusion.

## The stale list

```markdown
## Possibly overtaken ADRs (named anchors missing at the end of the range)

- ADR-9 ADR-9/4: missing 'ChatRunner', 'ChatRequest', 'ChatReply'
- 3 already in the baseline
```

Once per run, at the end of the range, adrcheck looks for every name and path every accepted ADR's
obligations mandate. Presence is tested against code only; a mention in a comment, a docstring or a
markdown file does not count. An obligation whose anchors are all gone is listed. One surviving anchor is
a foothold and the row is not listed.

The list is about the repository's state, not about the commits you checked, which is why it has its own
section. Rows you have reviewed and recorded with `--write-baseline` are counted, not listed. The baseline
file is `.adrcheck/baseline.json` and you edit it like source.

## Hygiene codes

`adrcheck lint` reads the ADR set and nothing else. No model.

| Code | Meaning |
|---|---|
| `missing-status` | no recognisable Status; the ADR cannot be enforced or excluded |
| `no-binding-section` | an Accepted ADR with no Decision or Consequences section; nothing binds |
| `duplicate-number` | two files share a number |
| `dangling-supersede-ref` | `Supersedes: ADR-9`, and there is no ADR-9 |
| `status-mismatch` | ADR-3 is superseded by ADR-7, but ADR-3's status is not Superseded. Not raised while ADR-7 is still Proposed |
| `self-supersede` | an ADR names itself in Supersedes or Superseded by |
| `multiple-supersede-targets` | one ADR superseded by two; one decision has one successor |
| `supersede-cycle` | ADR-3 supersedes ADR-5 supersedes ADR-3 |
| `scope-disagreement` | the ADR's `Applies to` header and the repo-side map disagree; the header wins |
| `map-unknown-adr` | `.adrcheck/map.toml` names an ADR that does not exist |

`check` prints scope issues to stderr as well, so a stale map is visible where you run.

## Exit codes

| Code | `check` | `lint` | `compile` | `eval` |
|---|---|---|---|---|
| 0 | no CONFLICT, or none with `--fail-on` | clean | compiled | every case hit |
| 1 | no ADR directory found | issues found, or no ADR directory | no ADR directory found | at least one miss |
| 2 | a verified CONFLICT with `--fail-on conflict` | | | |
| 3 | could not evaluate | | model unreachable | could not run |

Could not evaluate means no key, the provider down, or every judge call failing. It is printed with its
reason on stderr. The GitHub Action reports it as a warning and does not fail the step, because an
unreachable model is not a finding about your code. In a shell or a pre-commit hook it is an ordinary
non-zero exit, and the hook configuration decides whether that blocks the commit.
