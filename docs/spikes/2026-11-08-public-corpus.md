# First public corpus: i-dot-ai/consult (2026-11-08)

Bead: adrcheck-4zu. The first run of adrcheck on a repository nobody here wrote. Chosen from a GitHub code
search for numbered ADR files: Python, MIT licence, 18 ADR files under `docs/architecture/decisions`
(the adr-tools default path), active in November 2026. Raw output: `2026-11-08-public-corpus.run.json`.

## The corpus

| | |
|---|---|
| repository | github.com/i-dot-ai/consult, MIT |
| ADR files | 18, Nygard shape with `## Status` as a section; two pairs share a number (7 and 14) |
| statuses | 16 accepted, 1 superseded, 1 proposed |
| `Applies to` lines | none, so every accepted ADR goes to the judge on every code commit |
| compiled obligations | 173 from 16 ADRs: 64 mechanical, 65 structural, 28 intent, 16 process |
| range | `HEAD~6..HEAD`, six squash-merged pull requests of 2026-11-06 |

## Cost

| Step | Calls | Tokens in | Cost |
|---|---|---|---|
| compile 16 ADRs | 16 | | about $1.10, estimated from earlier per-ADR compiles; the run that compiled them died before printing its total (see below) |
| judge 6 commits | 6 | 616k | $1.41 as reported by `claude -p` |

Per commit: 81k to 138k tokens in, $0.17 to $0.43. The lower bound is the floor for a repository whose
ADRs carry no scope: sixteen ADRs' binding text and obligations ride along with every diff, even a
one-line CODEOWNERS change.

## Verdicts

No CONFLICT. Eighteen rows as printed; sixteen once the duplicate-number bug below is removed.

| Commit | What changed | Judged relevant | Rows |
|---|---|---|---|
| dfdaad72 | CODEOWNERS | none | ADR-7 (both records) COMPLIANT, nothing cited |
| 2e737117 | PR reviewer script and workflow | none | ADR-7 (both records) COMPLIANT, nothing cited |
| e1e037ec | release workflow, Makefile, Dockerfile hotfix | ADR-7 (release workflows) | COMPLIANT, cites the added ENVIRONMENT input |
| f36396b1 | evaluation tracing, 16 files | ADR-10, 11, 13 | ADR-13: 1 COMPLIANT, 1 ADR-OVERTAKEN, 3 UNCLEAR; 10 and 11 COMPLIANT with nothing cited |
| 6f5e77c2 | benchmark folded into run_eval, 19 files, edits ADR-13 itself | ADR-13 | 4 COMPLIANT, 1 ADR-OVERTAKEN, 1 UNCLEAR |
| 340a76d7 | comparison fixes | ADR-13 | COMPLIANT, nothing cited |

ADR-13 (modular evaluation framework) is the one ADR these commits really touch, and it was edited in
6f5e77c2 together with the code. The two ADR-OVERTAKEN rows are its obligation about a Langfuse context:
the parent commit already used platform-neutral run labels, so the change did not introduce the gap. The
four UNCLEAR rows are about where Langfuse-specific code may live, which the diff alone does not settle.
No label from a maintainer exists for any row; these are the judge's words, not ground truth.

## The stale sweep on a brownfield repository

As run, 19 stale rows across 8 of 16 ADRs: anchors such as `SQS`, `meta.json`, `question_part.json`,
`confirmed_themes`, `dataset_id`. Checked by hand against the committed tree: every one is absent from code
(the only hits were adrcheck's own cache). So these are not probe noise; they are early ADRs whose named
files, fields and services the code no longer carries, or carries under other names. Whether each is
staleness or a renamed anchor is a question only the maintainers can answer.

Under the all-anchors rule, 9 rows across 5 ADRs remain (3, 6, 7, 8, 15). Either way a first run on a
three-year-old decision log will list several ADRs as possibly overtaken. That is the brownfield baseline
problem (adrcheck-yi8): the first run should write the list down, and later runs should report only what
changed.

## Four defects the run found in adrcheck

1. **A binary blob ended the run.** The presence probe and post-image reads decoded every `git show`
   as UTF-8; an icon in the tree raised and the check exited 3 after compiling all 16 ADRs. Fixed in
   d9728f6 (decode with replacement). Exit 3 reported it correctly, which is what it is for.
2. **Two records sharing a number printed every finding twice.** Findings were keyed by ADR number; now by
   case position. Fixed in 27dc6bb. Lint also reports `duplicate-number` now (35533f1).
3. **The stale sweep fired on any missing anchor.** ADR-5 says all anchors must be gone. The code predated
   the ADR, so by adrcheck's own rule the ADR had been overtaken by its code. Fixed in 27dc6bb.
4. **The adr-tools path was not found.** `docs/architecture/decisions` is far more common than
   `docs/adr`; the CLI now discovers the conventional directories (35533f1).

## What a maintainer would need from us before this is useful to them

- Scope lines (`Applies to`) or an external ADR-to-path map, so a CODEOWNERS edit costs nothing.
- A baseline for the stale list and for "judged, not relevant", so the first run is a report and the
  second run is a diff.
- A way to say which of the nine stale rows are real; the fix is theirs (amend or deprecate the ADR),
  not ours.

Day's model spend so far: about $3 on this corpus, about $3.60 including the recompiles and probes
earlier in the day.
