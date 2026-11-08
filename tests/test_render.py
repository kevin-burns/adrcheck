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
