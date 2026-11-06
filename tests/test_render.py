import json

from adrcheck.adapters.render import to_json, to_markdown
from adrcheck.domain.verdict import Verdict
from adrcheck.usecases.check import ChangeReport, Excluded, Finding

REPORT = ChangeReport(
    ref="abc1234",
    message="store: key by url",
    findings=(Finding(2, "ADR-2/1", Verdict.CONFLICT, frozenset({"glob"}), path="enrich/store.py", line_text='key = row["url"]', quote="keyed by store.row_key", reason="keys by url"),),
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
