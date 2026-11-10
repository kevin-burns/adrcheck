import json

from adrcheck.adapters.render import to_json, to_markdown
from adrcheck.domain.verdict import Verdict
from adrcheck.usecases.check import ChangeReport, Excluded, Finding

REPORT = ChangeReport(
    ref="abc1234",
    message="store: key by url",
    findings=(
        Finding(
            2,
            "ADR-2/1",
            Verdict.CONFLICT,
            frozenset({"glob"}),
            path="enrich/store.py",
            line_text='key = row["url"]',
            quote="keyed by store.row_key",
            reason="keys by url",
            adr_blob="2b1f0a9c",
        ),
    ),
    excluded=(Excluded(7, "globs did not match any changed path"),),
    uncovered=1,
    judge_calls=1,
    cost_usd=0.02,
)


def test_json_has_one_record_per_finding_with_the_spike_fields():
    rows = json.loads(to_json([REPORT]))
    [row] = rows["findings"]
    assert row["commit"] == "abc1234" and row["adr"] == 2 and row["verdict"] == "CONFLICT"
    assert row["signals"] == ["glob"] and row["label"] == "" and row["note"] == ""
    assert row["adr_blob"] == "2b1f0a9c"
    assert rows["changes"][0]["uncovered"] == 1


def test_markdown_shows_verdict_line_and_quote():
    md = to_markdown([REPORT])
    assert "CONFLICT" in md and 'key = row["url"]' in md and "keyed by store.row_key" in md


def test_markdown_names_the_adrs_the_judge_dismissed_so_judged_is_not_mistaken_for_not_selected():
    report = ChangeReport(
        ref="abc1234",
        message="m",
        findings=(),
        excluded=(
            Excluded(2, "model: not relevant to this change"),
            Excluded(7, "model: not relevant to this change"),
            Excluded(9, "globs did not match any changed path"),
        ),
        judge_calls=1,
    )
    md = to_markdown([report])
    assert "- judged, not relevant: ADR-2, ADR-7" in md
    assert "ADR-9" not in md
    assert "_No ADR applied to this change._" not in md


def test_markdown_is_lint_clean_with_blank_lines_after_headings_and_around_lists():
    md = to_markdown([REPORT])
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## "):
            assert lines[i + 1] == "", f"no blank line after heading at {i}"
            assert i == 0 or lines[i - 1] == "", f"no blank line before heading at {i}"


def test_stale_rows_known_from_the_baseline_are_counted_not_listed():
    from adrcheck.usecases.check import StaleAdr

    report = ChangeReport(
        ref="abc1234",
        message="m",
        stale=(StaleAdr(4, "ADR-4/2", ("import_rows",), known=True), StaleAdr(5, "ADR-5/1", ("Clef",))),
    )
    md = to_markdown([report])
    assert "- ADR-5 ADR-5/1: missing 'Clef'" in md
    assert "ADR-4/2" not in md and "1 already in the baseline" in md
    assert [s["known"] for s in json.loads(to_json([report]))["stale"]] == [True, False]


def test_a_proposed_adr_whose_paths_the_change_touched_gets_its_own_line():
    report = ChangeReport(
        ref="abc1234",
        message="m",
        excluded=(
            Excluded(7, "status is proposed; this change touches its paths, not enforced"),
            Excluded(8, "status is proposed"),
        ),
    )
    md = to_markdown([report])
    assert "- proposed, not enforced, touches its paths: ADR-7" in md and "ADR-8" not in md


def _finding(**kw):
    base = {
        "adr_number": 2,
        "obligation_id": "ADR-2/1",
        "verdict": Verdict.CONFLICT,
        "signals": frozenset(),
        "path": "a.py",
    }
    return Finding(**{**base, **kw})


def test_judge_text_cannot_start_a_new_markdown_block_or_hide_html_in_the_comment():
    reason = "keys by url\n\n## Injected heading\n<!-- adrcheck-report --> <img src=x>"
    md = to_markdown([ChangeReport(ref="abc", message="m", findings=(_finding(reason=reason),))])
    assert "\n## Injected" not in md and "<!--" not in md and "<img" not in md
    assert "  - keys by url ## Injected heading &lt;!-- adrcheck-report --> &lt;img src=x>" in md


def test_a_backtick_in_a_cited_line_or_path_stays_inside_its_code_span():
    md = to_markdown([ChangeReport(ref="abc", message="m", findings=(_finding(path="a`b.py", line_text="x = `y`"),))])
    assert "`a'b.py`: `x = 'y'`" in md


def test_judge_text_is_bounded_so_one_finding_cannot_fill_the_comment():
    md = to_markdown([ChangeReport(ref="abc", message="m", findings=(_finding(reason="r" * 2000, quote="q" * 2000),))])
    lines = [ln for ln in md.splitlines() if ln.startswith("  - ")]
    assert all(len(ln) < 320 for ln in lines) and all(ln.endswith("…") for ln in lines)


def test_findings_are_ordered_by_adr_then_by_how_bad_the_verdict_is():
    report = ChangeReport(
        ref="abc1234",
        message="m",
        findings=(
            _finding(adr_number=7, obligation_id="ADR-7/1", verdict=Verdict.COMPLIANT),
            _finding(adr_number=2, obligation_id="ADR-2/3", verdict=Verdict.COMPLIANT),
            _finding(adr_number=2, obligation_id="ADR-2/1", verdict=Verdict.CONFLICT),
            _finding(adr_number=2, obligation_id="ADR-2/2", verdict=Verdict.UNCLEAR),
        ),
    )
    lines = to_markdown([report]).splitlines()
    heads = [ln for ln in lines if ln.startswith("- **")]
    # one head per ADR, worst verdict first, ordered by ADR number; the obligations sit under the ADR
    assert [h.split()[1:3] for h in heads] == [["**CONFLICT**", "ADR-2"], ["**COMPLIANT**", "ADR-7"]]
    under = [ln.split()[1:3] for ln in lines if ln.startswith("  - **")]
    assert under == [["**CONFLICT**", "ADR-2/1"], ["**UNCLEAR**", "ADR-2/2"], ["**COMPLIANT**", "ADR-2/3"]]


def test_several_findings_for_one_adr_collapse_under_one_head_line_that_counts_them():
    """rnr: the removal of one importer produced four CONFLICT rows for one ADR at one commit. One head per
    (commit, ADR) with the worst verdict and the tally; each obligation beneath it with its line, quote and
    reason. A lone finding for an ADR stays a single line, as before."""
    report = ChangeReport(
        ref="abc1234",
        message="m",
        findings=(
            _finding(
                adr_number=4,
                obligation_id="ADR-4/1",
                verdict=Verdict.CONFLICT,
                path="enrich/store.py",
                line_text='key = row["url"]',
            ),
            _finding(adr_number=4, obligation_id="ADR-4/2", verdict=Verdict.CONFLICT),
            _finding(adr_number=4, obligation_id="ADR-4/3", verdict=Verdict.COMPLIANT),
            _finding(adr_number=9, obligation_id="ADR-9/1", verdict=Verdict.COMPLIANT),
        ),
    )
    md = to_markdown([report])
    assert "- **CONFLICT** ADR-4 (3 obligations: 2 CONFLICT, 1 COMPLIANT)" in md
    assert "  - **CONFLICT** ADR-4/1" in md and "  - **COMPLIANT** ADR-4/3" in md
    assert '    - `enrich/store.py`: `key = row["url"]`' in md  # the obligation's evidence is nested one level deeper
    assert "- **COMPLIANT** ADR-9 (ADR-9/1)" in md  # a lone finding keeps the flat shape


def test_compliant_verdicts_with_nothing_to_cite_share_one_line_instead_of_one_bare_line_each():
    """A judge that returns no finding for a selected ADR leaves a COMPLIANT with no obligation, line or quote.
    Six of those in a row say nothing a reader needs six lines for."""
    report = ChangeReport(
        ref="abc1234",
        message="m",
        findings=(
            _finding(adr_number=2, obligation_id=None, verdict=Verdict.COMPLIANT, path=""),
            _finding(adr_number=3, obligation_id=None, verdict=Verdict.COMPLIANT, path=""),
            _finding(adr_number=5, obligation_id="ADR-5/1", verdict=Verdict.COMPLIANT, path="a.py", reason="ok"),
        ),
    )
    md = to_markdown([report])
    assert "- compliant, nothing to cite: ADR-2, ADR-3" in md
    assert "- **COMPLIANT** ADR-2" not in md and "- **COMPLIANT** ADR-5 (ADR-5/1)" in md


def test_codequality_renders_findings_in_the_code_climate_shape_gitlab_reads():
    """GitLab's merge-request widget reads a Code Quality artifact: a JSON list of issues with description,
    check_name, fingerprint, severity and a location. No token, no API call: the cheapest GitLab surface."""
    from adrcheck.adapters.render import to_codequality

    rows = json.loads(to_codequality([REPORT]))
    [row] = rows
    assert row["check_name"] == "adrcheck/ADR-2" and row["severity"] == "major"
    assert row["location"] == {"path": "enrich/store.py", "lines": {"begin": 1}}
    assert "keyed by store.row_key" in row["description"] and "keys by url" in row["description"]
    assert len(row["fingerprint"]) == 64  # sha256 of ADR, obligation, path and line: stable across runs and pushes
    assert row["type"] == "issue" and row["categories"] == ["Style"]


def test_codequality_maps_the_other_verdicts_to_lower_severities_and_skips_compliant():
    from adrcheck.adapters.render import to_codequality

    report = ChangeReport(
        ref="abc1234",
        message="m",
        findings=(
            _finding(adr_number=2, obligation_id="ADR-2/1", verdict=Verdict.UNCLEAR, line_text="x = 1"),
            _finding(adr_number=3, obligation_id="ADR-3/1", verdict=Verdict.ADR_OVERTAKEN, line_text="y = 2"),
            _finding(adr_number=4, obligation_id="ADR-4/1", verdict=Verdict.COMPLIANT, line_text="z = 3"),
        ),
    )
    rows = json.loads(to_codequality([report]))
    assert [(r["check_name"], r["severity"]) for r in rows] == [("adrcheck/ADR-2", "minor"), ("adrcheck/ADR-3", "info")]


def test_codequality_fingerprint_does_not_change_with_the_commit():
    """GitLab diffs a merge request's report against the target branch's by fingerprint, and shows the same
    issue once across pushes. Both need the fingerprint to name the finding, not the commit it was seen on."""
    from dataclasses import replace

    from adrcheck.adapters.render import to_codequality

    first = json.loads(to_codequality([REPORT]))
    second = json.loads(to_codequality([replace(REPORT, ref="fffffff")]))
    assert first[0]["fingerprint"] == second[0]["fingerprint"]


def test_codequality_location_uses_the_finding_line_number_when_known():
    from adrcheck.adapters.render import to_codequality

    report = ChangeReport(
        ref="abc1234",
        message="m",
        findings=(_finding(line_text="x = 1", line_number=7), _finding(obligation_id="ADR-2/2", line_text="y = 2")),
    )
    rows = json.loads(to_codequality([report]))
    assert [r["location"]["lines"]["begin"] for r in rows] == [7, 1]
