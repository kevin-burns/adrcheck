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
