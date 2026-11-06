# Spike: adrcheck on job-search, 2026-11-06

**Go/no-go against the targets set in frontier Q9, before Kevin's labels:**

| Target | Result |
|---|---|
| Zero false alarms on clean commits | Not yet labelled. 7 CONFLICT findings are in the sheet below; 4 are the planted stale ADR at the commit that removed its subject (expected), 2 are ADR-1 at 7644413 (plausible, letter of the ADR), 1 is ADR-2 at 3c11d0b (the judge's own 2/7 finding on the same line says COMPLIANT, so likely a false alarm). |
| Every planted conflict fires | Yes. The removal of the LinkedIn importer (614a20d) produced CONFLICT on 4 of ADR-4's obligations. |
| Stale ADR comes back ADR-OVERTAKEN, not CONFLICT | Yes, by the stale sweep at the range end: ADR-4 is the only ADR named, with `import_rows` missing from code. Per-diff classification could not do it, see "Design findings". |

Numbers are from one sonnet run over 20 commits, then re-settled offline with the rule fixes
below. The judge's claims were not re-generated; a fresh end-to-end run is bead `adrcheck-2nj`
(see follow-ups). The eval set is frozen only after Kevin labels the sheet.

## Method

- Repo: `~/Developer/job-search`, commits `285ff7e..3c11d0b` (20 commits, 2026-10-08 to 2026-11-06).
- ADRs: four Nygard ADRs written for the spike into `job-search/docs/adr/`. ADR-1 (one canonical
  key, `store.row_key`), ADR-2 (rows folded, never dropped), ADR-3 (every suppression carries a
  reason) describe rules the code really follows. ADR-4 (LinkedIn descriptions fetched per URN by
  `import_rows()`) is the planted stale one: its subject was deleted in 614a20d.
- Pipeline: `adrcheck check --range 285ff7e~1..3c11d0b --format json --model sonnet`. Selection by
  `Applies to:` globs plus ADR-id references; compile once per ADR (cached); one judge call per
  (commit, ADR) pair; verify() on every claim; parent probes for CONFLICT vs ADR-OVERTAKEN.
- Judge: sonnet via `claude -p --output-format json --tools ""`, cwd set to a temp dir.

## Numbers

| Measure | Value |
|---|---|
| Commits in range | 20 |
| Commits with any judge call | 9 (the other 11 changed only markdown; globs excluded every ADR) |
| Judge calls | 22 |
| Judge calls where the model said the ADR was not relevant | 11 of 22 |
| Findings | 28 (7 CONFLICT, 12 COMPLIANT, 9 UNCLEAR, 0 ADR-OVERTAKEN per finding) |
| Stale sweep hits at range end | 1 ADR (ADR-4, two obligations), the planted one |
| Claims that cited a line the commit did not change | 4 of 28 (caught by verify(), reported UNCLEAR or kept COMPLIANT with the failure listed) |
| Claims whose quote was not in Decision or Consequences | 0 |
| Abstention rate (UNCLEAR over findings) | 9 / 28 |
| Wall time, check run | 238 s |
| Model spend, check run | $3.34 (about $0.15 per judge call) |
| Model spend, compile (4 ADRs, second run, prompt cache warm) | $0.09. The first compile run did not print its cost; that was added afterwards. |
| Decision signals (Q29) | 7 fired, all `new-external-host` from job URLs in markdown notes, all junk. Prose files are now excluded; on this range the count would be 0. |

The 44k-token harness system prompt that `claude -p` carries is most of the per-call cost. The
SDK route would not pay it. Noted for the Action milestone.

## Defects found by reading the output, and fixed (all test-first, 75 tests green)

1. **verify() line rule too strict.** The judge drops indentation when it copies a line, and
   sometimes copies the `-` marker. 10 of 15 line failures were this. Now compared after
   stripping, with a copied marker tolerated only when the bare line does not match.
2. **Precedent probe fired on removed lines.** A removed line exists at the parent by
   definition, which turned a real CONFLICT (ADR-4/3) into ADR-OVERTAKEN. Now added lines only.
3. **Compiler invented anchors.** `fold_count`, `time.sleep`, `from store import row_key` appear
   in no ADR. Only anchors the ADR names verbatim are kept, and all must be present for the ADR
   to count as in force.
4. **Compiler `forbids` too broad** (`hashlib.`, `.filter(`) and would have flipped every ADR-1
   CONFLICT to overtaken. Classification no longer uses them; the "already violated" question
   is asked of the judge's own cited line.
5. **A mention is not a presence.** `import_rows` survived at HEAD in a docstring and in docs, so
   the stale sweep saw nothing. The probe now strips comments, docstrings and prose files, and
   also sees file paths, so an ADR that names a module is probed against the tree.
6. **Token re-join broke adjacency** in the first version of (5): `store.row_key(` became
   `store . row_key (` and ADR-1 looked overtaken. Removed spans are blanked in place now.

## Design findings

- **Stale detection cannot ride on the diff.** After 614a20d no commit touched linkedin.py, so
  ADR-4 was never selected again and per-diff classification never had the chance to say
  ADR-OVERTAKEN. The per-run stale sweep (named anchors present in code at the range end) is
  what catches it, with no model call. Q14's rule still applies per finding; the sweep is the
  second leg.
- **Half the judge spend was relevance filtering.** `enrich/**` selects every ADR for every
  enrichment commit, and the judge then says "not relevant" 11 times out of 22. Finer globs,
  or a cheap relevance pass before the sonnet judge, would roughly halve the cost.
- **The judge contradicts itself across obligations of one ADR.** At 3c11d0b the same line is
  CONFLICT for ADR-2/1 and COMPLIANT for ADR-2/7. One call per (commit, ADR) with all
  obligations is cheaper than one per obligation, but a per-ADR consistency check (or a
  per-ADR collapse in the report) is worth a bead.
- **Over-generation at compile.** 9 obligations for ADR-1, several near-duplicates. Harmless
  for correctness, costly in judge tokens and in report length.
- **The planted ADR produced four CONFLICT findings for one event.** The report should
  collapse findings per ADR per commit with the strongest verdict first.

## Not done

- No human labels yet, so no false-alarm rate is published. The sheet below is the labelling
  input (Q32: Kevin labels, checker output never seeds expected files).
- No fresh end-to-end run with the fixed rules; the numbers above re-settle saved claims.
- Q4's measurement (how often model-only selection would have picked the right ADRs) was not
  run; selection used globs throughout.
- `adrcheck eval` and the fixture freeze (Q31) wait for labels.
- `--staged` is a stub.

## Labelling sheet

Labels: TP (real conflict), FP (false alarm), TN (compliant and right), FN-abstained (UNCLEAR
on a real conflict), misclass (right to flag, wrong class), ok-abstain (UNCLEAR and the diff
really does not settle it).

| # | Commit | ADR / obligation | Verdict | Changed line | ADR quote | Judge's reason | verify() | 2nd opinion (blind Sonnet) | Label |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3c11d0b | ADR-2 ADR-2/1 | CONFLICT | `twin.setdefault("also", []).append(url)` | A row the pipeline decides not to show is folded, not dropped: it stays in the d | The LinkedIn duplicate is never added to the row list: only its URL is appended to the twin's 'also' list and the loop continues, so the dup | ok | COMPLIANT ≠ (ADR ambiguous) |  |
| 2 | 614a20d | ADR-4 ADR-4/1 | CONFLICT | `"""Read LinkedIn postings from the li-assist cache, in the shape job-f` | `enrich/linkedin.py` owns LinkedIn ingestion end to end. | The module docstring now says linkedin.py only reads the cache and 'NO FETCHING HERE', and the import_rows() entry point is removed, so it n | ok | CONFLICT (letter-only; ADR ambiguous) |  |
| 3 | 614a20d | ADR-4 ADR-4/2 | CONFLICT | `NO FETCHING HERE. Descriptions are fetched by bin/li-descriptions.py u` | `import_rows()` fetches each posting's description per URN through `li-assist jo | import_rows() and \_fetch() (the `li-assist jobs get` call) are deleted, so nothing in enrich/linkedin.py fetches per URN any more. | ok | CONFLICT (cited line not in diff as quoted (docstring line is the nearest added line)) |  |
| 4 | 614a20d | ADR-4 ADR-4/3 | CONFLICT | `DELAY = 1.2  # a courtesy gap; li-assist is session-based and throttle` | with a courtesy delay between calls | The DELAY constant and the time.sleep courtesy delay are removed along with the fetch loop in enrich/linkedin.py. | ok | CONFLICT (letter-only; cited line removed not added) |  |
| 5 | 614a20d | ADR-4 ADR-4/5 | CONFLICT | `-     try:` | A failed fetch skips its row rather than failing the run. | The try/except that skipped a row on failed fetch is deleted along with the fetch path, so the skip-on-failed-fetch behaviour no longer exis | ok | UNCLEAR ≠ (ADR ambiguous; cited line removed not added) |  |
| 6 | 7644413 | ADR-1 ADR-1/4 | CONFLICT | `PRIMARY KEY (content_hash, rubric));` | Every table in `enrich/` is keyed on it and nothing else. | The new triage table is keyed on (content_hash, rubric), so it is keyed on the row key plus the rubric version, not on the row key alone. | ok | CONFLICT (letter-only) |  |
| 7 | 7644413 | ADR-1 ADR-1/6 | CONFLICT | `r["hash"] = store.content_hash(r["text"])` | Any new store, cache or report index in `enrich/` calls `store.row_key`. | The new triage cache gets its key from store.content_hash on pre-stripped text instead of calling store.row_key(description). | ok | CONFLICT (letter-only) |  |
| 8 | 3c11d0b | ADR-1 ADR-1/5 | UNCLEAR | `boards_by_role = {_role(r["company"], r["title"]): r for r in rows}` | No module builds a key by hand from a URL, a URN, a title or a raw description. | The new `_role(company, title)` key is hand-built from a title and used as a lookup key, but it is a transient in-memory dedupe key rather t | ok | CONFLICT ≠ (letter-only) |  |
| 9 | 3c11d0b | ADR-2 ADR-2/2 | UNCLEAR | `f"  {r['url']}" + (f" (also on: {', '.join(r['also'])})" if r.get("als` | it is counted, and the count is visible in the report | The report prints the folded copy's links as 'also on:', but the diff shows no count of folded duplicates anywhere in the report. | line-not-in-change | CONFLICT ≠ (letter-only; ADR ambiguous) |  |
| 10 | 3c11d0b | ADR-2 ADR-2/3 | UNCLEAR | `f"  {r['url']}" + (f" (also on: {', '.join(r['also'])})" if r.get("als` | with a control that restores the rows | The diff adds no control that restores the folded LinkedIn copy as a row; it only lists its URL as text. | line-not-in-change | UNCLEAR (ADR ambiguous) |  |
| 11 | 614a20d | ADR-4 ADR-4/4 | UNCLEAR | `Read LinkedIn postings from the li-assist cache, in the shape job-feed` | lands the rows in the shape job-feeds uses | import_rows() is gone but cached_rows() still maps to the job-feeds row shape, so whether the 'import_rows() must land rows' obligation is m | line-not-in-change | COMPLIANT ≠ |  |
| 12 | 614a20d | ADR-4 ADR-4/7 | UNCLEAR | `URN = re.compile(r"^urn:li:fsd_jobPosting:\d+$")` | The URN is validated before it reaches the subprocess. | The URN validation and subprocess call were removed together, so no unvalidated URN reaches a subprocess here, but the diff does not show wh | ok | UNCLEAR (ADR ambiguous; cited line removed not added) |  |
| 13 | 614a20d | ADR-4 ADR-4/6 | UNCLEAR | ``- Fetching is done by `bin/li-descriptions.py`, which the design does`` | No other module calls `li-assist`. | The drift report states that bin/li-descriptions.py does the fetching, which suggests another module invokes li-assist, but the diff does no | ok | ADR-OVERTAKEN ≠ (ADR ambiguous) |  |
| 14 | 74a45f6 | ADR-2 ADR-2/5 | UNCLEAR | `except Exception as e:  # one malformed reply must not lose the other` | The only rows that may leave the data are ones whose source row was removed. | The new except branch keeps a failed row in results as 'not screened' rather than dropping it, which looks compliant, but the diff does not  | ok | COMPLIANT ≠ |  |
| 15 | ce31958 | ADR-1 ADR-1/7 | UNCLEAR | `by_hash[store.content_hash(r["text"])].append(r)` | A module that needs a key imports it rather than hashing locally. | The new recheck_cache builds its posting key with store.content_hash(r["text"]) instead of store.row_key; the text is already stripped, so t | ok | COMPLIANT ≠ (ADR ambiguous) |  |
| 16 | ce31958 | ADR-1 ADR-1/4 | UNCLEAR | `conn.execute("UPDATE triage SET payload = ? WHERE content_hash = ? AND` | Every table in `enrich/` is keyed on it and nothing else. | The new rewrite_triage addresses the triage table by content_hash plus rubric rather than by row_key alone; the triage schema itself is not  | ok | ADR-OVERTAKEN ≠ (letter-only) |  |
| 17 | 2965846 | ADR-2 ADR-2/8 | COMPLIANT | `v = _text(f.get("value")) or "unstated"` | A triage pile is listed, never hidden. | The changed line only coerces a fact value to text when rendering the read/maybe piles; it does not hide, filter or drop any row or pile. | ok | UNCLEAR ≠ |  |
| 18 | 2965846 | ADR-2 ADR-2/1 | COMPLIANT | `v = _text(f.get("value")) or "unstated"` | A row the pipeline decides not to show is folded, not dropped: it stays in the d | The changed line only formats a field value inside the report and does not remove any row from the results. | ok | UNCLEAR ≠ |  |
| 19 | 3c11d0b | ADR-2 ADR-2/7 | COMPLIANT | `twin.setdefault("also", []).append(url)` | A duplicate folded into another row keeps its link on the surviving row. | The folded LinkedIn copy's URL is appended to the surviving board row's 'also' list and printed in the report. | ok | COMPLIANT |  |
| 20 | 418f2e4 | ADR-2 ADR-2/8 | COMPLIANT | `return "maybe" if unverified_stated or obstacle_basis in ASSUMED else` | A triage pile is listed, never hidden. | The changed cut rule sends a both-no row to the listed maybe pile instead of the no pile when the obstacle is only inferred or unstated, so  | ok | COMPLIANT |  |
| 21 | 418f2e4 | ADR-2 ADR-2/2 | COMPLIANT | `lines += [f"## {name} ({len(rows)})", ""]` | it is counted, and the count is visible in the report | Each of the three new groups (read, open maybe, stated maybe) prints its row count in its heading, and maybe_group puts every maybe row into | ok | COMPLIANT |  |
| 22 | 5bbd7be | ADR-1 ADR-1/4 | COMPLIANT | `res["profile_sha"] = profile_sha` | Every table in `enrich/` is keyed on it and nothing else. | The profile hash is written into the card payload, not into the triage table key, and the added comment says it is stored 'in the payload ra | ok | COMPLIANT (ADR ambiguous) |  |
| 23 | 614a20d | ADR-4 ADR-4/8 | COMPLIANT | `def cached_rows(path=None):` | a report missing badges beats a report that does not generate. | cached_rows() reads only the local cache with no network and returns no rows on a missing cache, so report generation does not depend on the | line-not-in-change | COMPLIANT (cited line not in diff) |  |
| 24 | 74a45f6 | ADR-2 ADR-2/8 | COMPLIANT | `"verdict": "not screened",` | A triage pile is listed, never hidden. | A row whose reply fails is turned into a 'not screened' result and appended to results instead of being discarded, so it stays in the data t | ok | COMPLIANT |  |
| 25 | 7644413 | ADR-2 ADR-2/8 | COMPLIANT | `lines += [f"## no ({len(piles['no'])}) — both tiers said no", ""]` | A triage pile is listed, never hidden. | The report emits a '## no' section that lists every row in the no pile, so the pile is listed, not hidden. | ok | COMPLIANT |  |
| 26 | 7644413 | ADR-2 ADR-2/2 | COMPLIANT | `f"{len(results)} adverts: "` | it is counted, and the count is visible in the report | The report header prints a per-pile count (read, maybe, no, not screened) and the no section heading repeats the no count, so the number of  | ok | COMPLIANT |  |
| 27 | ce31958 | ADR-2 ADR-2/5 | COMPLIANT | `conn.execute("UPDATE triage SET payload = ? WHERE content_hash = ? AND` | The only rows that may leave the data are ones whose source row was removed. | The new rewrite_triage path runs an UPDATE on the payload and deletes no triage rows, so no row leaves the data. | ok | UNCLEAR ≠ |  |
| 28 | ce31958 | ADR-2 ADR-2/1 | COMPLIANT | `return "maybe" if listing_only and skills_fit in ("strong", "partial")` | A row the pipeline decides not to show is folded, not dropped: it stays in the d | The new cut() branch only moves fitting rows from no to maybe, and recheck_cache rewrites verdicts in place, so no rows are removed from the | ok | COMPLIANT |  |

Stale sweep at the range end (3c11d0b), no model call:

- ADR-4 ADR-4/1: named anchor(s) missing from code: import_rows
- ADR-4 ADR-4/2: named anchor(s) missing from code: import_rows

Per-commit judge spend:

| Commit | Subject | Judge calls | Cost USD | Uncovered files | Model said not relevant |
|---|---|---|---|---|---|
| 285ff7e | APPLY-NOW: personal sweep notes (subject withheld) | 0 | 0.00 | 1 |  |
| 21be543 | APPLY-NOW: personal sweep notes (subject withheld) | 0 | 0.00 | 2 |  |
| 27f1aa5 | job-triage skill brief + spike results (granite vs Haiku 5.5 | 0 | 0.00 | 4 |  |
| a0ec713 | job-triage brief: middle-ground rubric, flexible 24h-7d wind | 0 | 0.00 | 1 |  |
| 7644413 | job-triage: fact-card triage engine (Haiku 5.5 + tev1, grani | 2 | 0.41 | 2 |  |
| 74a45f6 | job-triage: accept list-valued fields; one bad reply no long | 2 | 0.20 | 0 | ADR-1 |
| 2965846 | job-triage: report accepts list values from older cards | 2 | 0.20 | 0 | ADR-1 |
| 33678de | job-triage: report spend counts only newly carded adverts | 2 | 0.22 | 3 | ADR-1, ADR-2 |
| 418f2e4 | job-triage: obstacle basis + strong-fit open maybes listed f | 2 | 0.27 | 1 | ADR-1 |
| d31ddba | job-triage brief: rubric .2, granite 4.1 vs Haiku, effort te | 0 | 0.00 | 1 |  |
| bb86f9e | job-triage: keep eval iteration-1 workspace; ignore generate | 0 | 0.00 | 30 |  |
| 1a8f3d7 | APPLY-NOW: personal sweep notes (subject withheld) | 0 | 0.00 | 1 |  |
| 5bbd7be | triage: a profile edit makes cached decisions stale | 2 | 0.32 | 2 | ADR-2 |
| 693a441 | APPLY-NOW: personal sweep notes (subject withheld) | 0 | 0.00 | 1 |  |
| 4264f0c | APPLY-NOW: personal sweep notes (subject withheld) | 0 | 0.00 | 1 |  |
| d488966 | APPLY-NOW: personal sweep notes (subject withheld) | 0 | 0.00 | 1 |  |
| ce31958 | triage: verify quotes against the labelled header; a listed  | 2 | 0.39 | 1 |  |
| 2f0d41c | triage: put the run time in the report name so a second run  | 2 | 0.30 | 3 | ADR-1, ADR-2 |
| 614a20d | Remediate the 2026-11-06 drift check: specs record what was  | 3 | 0.55 | 6 | ADR-1, ADR-2 |
| 3c11d0b | Badge aggregator rows with no employer board; fold a LinkedI | 3 | 0.48 | 2 | ADR-3 |

## Second opinion: blind Sonnet reader (2026-11-06)

Kevin could not label the sheet from the rows alone, so a Sonnet subagent with read access to the
job-search repository re-judged all 28 findings **blind**: it saw the commit, the ADR, the quoted
obligation and the cited line, but not the judge's verdict. Same model family as the judge, more
evidence (whole repo, parent commits, callers). These are **rater labels, not ground truth**; they
measure agreement between two readings, the same caveat as the decision-models post.
Raw TSV: `2026-11-06-job-search.second-opinion.tsv` (row numbers follow the JSON order, which
differs from the sheet above; match on commit + obligation).

Agreement 16/28.

| judge \ second | CONFLICT | COMPLIANT | UNCLEAR | ADR-OVERTAKEN |
|---|---|---|---|---|
| CONFLICT | 5 | 1 | 1 | 0 |
| COMPLIANT | 0 | 9 | 3 | 0 |
| UNCLEAR | 2 | 3 | 2 | 2 |

What the disagreements are:

- **One hard reversal.** 3c11d0b ADR-2/1: judge CONFLICT, second COMPLIANT (the duplicate's URL is
  kept on the surviving row). The judge's own 2/7 on the same line also said COMPLIANT. Label: FP.
- **Two ADR-OVERTAKEN the judge missed.** ce31958 ADR-1/4 (the composite key already existed at the
  parent) and 614a20d ADR-4/6 (`bin/li-descriptions.py` has called li-assist since 2026-09-05).
  The second reader also notes `import_rows()` had no caller before 614a20d, so the "planted
  conflict" commit deleted dead code; by the Q14 rule those ADR-4 CONFLICTs are arguably OVERTAKEN.
  The current precedent probe cannot see this: it looks for the judge's cited ADDED line at the
  parent, and these are removals. Needs a dead-code probe (bead adrcheck-ihg).
- **Judge over-asserts COMPLIANT** on lines that do not touch the obligation (2965846 ADR-2/8 and
  2/1, ce31958 ADR-2/5): second says UNCLEAR, "display-only, not this obligation". Harmless, but it
  inflates COMPLIANT and is what an obligation-level relevance gate would remove.
- **Judge over-abstains** where the diff does settle it (74a45f6 ADR-2/5, ce31958 ADR-1/7, 614a20d
  ADR-4/4): second says COMPLIANT with medium confidence.
- **Letter-only conflicts.** 7644413 ADR-1/4 and 1/6 both readers call CONFLICT, both mark
  letter-only: the ADR says "keyed on it and nothing else" and "calls store.row_key"; the code uses
  (content_hash, rubric) and content_hash on stripped text, same value in practice. 3c11d0b ADR-1/5
  (hand-built (company, title) lookup key) second calls CONFLICT letter-only where judge abstained.

ADR text problems the second reader surfaced (for the ADR author, not the checker):

1. ADR-1 must say whether a versioned composite key and a direct `content_hash` call are allowed.
2. ADR-4 is stale throughout and should be marked Deprecated or Superseded; its "No other module
   calls li-assist" sentence contradicts its own `Applies to` list, which names `bin/li-descriptions.py`.
3. ADR-2's "counted, with a control that restores the rows" is written for the HTML report; the
   markdown triage report has no controls, so 2/2 and 2/3 cannot be satisfied there.
4. ADR-1/5 does not say whether an in-memory dedupe key counts as "building a key by hand".
