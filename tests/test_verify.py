from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.verify import Claim, verify

ADR = Adr(
    title="One canonical key",
    status=Status.ACCEPTED,
    source="docs/adr/0002-one-key.md",
    number=2,
    sections={
        "context": "Rows used to be keyed by URL, which changed between sweeps.",
        "decision": "Every row is keyed by store.row_key and nothing else.",
        "consequences": "Callers never build a key by hand.",
    },
)
CHANGE = Change(
    ref="abc123",
    message="store: key by url again",
    files=(
        FileChange(
            path="enrich/store.py",
            old_path="enrich/store.py",
            added=(Line(path="enrich/store.py", kind="+", number=11, text='    key = row["url"]'),),
            removed=(Line(path="enrich/store.py", kind="-", number=11, text="    key = row_key(row)"),),
        ),
    ),
)


def claim(**overrides):
    base = dict(
        adr_number=2,
        path="enrich/store.py",
        line_text='    key = row["url"]',
        quote="keyed by store.row_key and nothing else",
    )
    base.update(overrides)
    return Claim(**base)


def test_a_claim_with_a_changed_line_and_a_decision_quote_verifies():
    assert verify(claim(), CHANGE, ADR).ok


def test_a_removed_line_counts_as_evidence():
    assert verify(claim(line_text="    key = row_key(row)"), CHANGE, ADR).ok


def test_a_line_the_change_did_not_touch_fails_line_rule():
    result = verify(claim(line_text="    db[key] = row"), CHANGE, ADR)
    assert not result.ok
    assert result.failed == ("line-not-in-change",)


def test_a_quote_not_in_the_adr_fails_quote_rule():
    result = verify(claim(quote="rows are keyed by uuid"), CHANGE, ADR)
    assert result.failed == ("quote-not-in-adr",)


def test_a_quote_from_context_fails_provenance_rule():
    result = verify(claim(quote="keyed by URL, which changed between sweeps"), CHANGE, ADR)
    assert result.failed == ("quote-outside-decision",)


def test_line_match_ignores_indentation_and_a_copied_diff_marker():
    assert verify(claim(line_text='key = row["url"]'), CHANGE, ADR).ok
    assert verify(claim(line_text='+     key = row["url"]'), CHANGE, ADR).ok
    assert verify(claim(line_text="- key = row_key(row)"), CHANGE, ADR).ok
