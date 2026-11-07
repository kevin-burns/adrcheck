"""Scoring a saved check report against frozen cases. No model, no git: pure comparison."""

from adrcheck.usecases.evaluate import Case, score

CASES = (
    Case(
        commit="7644413", adr=1, quote="Every table in `enrich/` is keyed on it and nothing else.", expected="CONFLICT"
    ),
    Case(commit="7644413", adr=2, quote="A triage pile is listed, never hidden.", expected="COMPLIANT"),
    Case(commit="3c11d0b", adr=2, quote="with a control that restores the rows", expected="UNCLEAR"),
    Case(
        commit="614a20d",
        adr=4,
        quote="a report missing badges beats a report that does not generate.",
        expected="COMPLIANT",
    ),
    Case(commit="3c11d0b", adr=2, quote="A duplicate folded into another row keeps its link.", expected="COMPLIANT"),
)
FINDINGS = [
    # same quote, longer in the report than in the case: still the same obligation
    {
        "commit": "7644413abcdef",
        "adr": 1,
        "quote": "Every table in `enrich/` is keyed on it and nothing else. Any new store",
        "verdict": "CONFLICT",
    },
    {"commit": "7644413abcdef", "adr": 2, "quote": "A triage pile is listed, never hidden.", "verdict": "UNCLEAR"},
    # an ADR-level COMPLIANT (no obligation, no quote) satisfies a COMPLIANT case for that ADR
    {"commit": "614a20d99", "adr": 4, "quote": "", "verdict": "COMPLIANT"},
]


def test_each_case_is_hit_missed_or_absent_and_the_matrix_counts_expected_against_got():
    result = score(CASES, FINDINGS)
    by = {(r.case.commit, r.case.adr, r.case.quote[:12]): (r.outcome, r.got) for r in result.rows}
    assert by[("7644413", 1, "Every table ")] == ("hit", "CONFLICT")
    assert by[("7644413", 2, "A triage pil")] == ("miss", "UNCLEAR")
    assert by[("3c11d0b", 2, "with a contr")] == ("absent", None)
    assert by[("614a20d", 4, "a report mis")] == ("hit", "COMPLIANT")
    # a COMPLIANT case nobody raised a finding against is silence, which is what COMPLIANT asks for
    assert by[("3c11d0b", 2, "A duplicate ")] == ("quiet", None)
    assert (result.hits, result.total) == (3, 5)
    assert result.matrix[("COMPLIANT", "UNCLEAR")] == 1
    assert result.matrix[("UNCLEAR", None)] == 1
