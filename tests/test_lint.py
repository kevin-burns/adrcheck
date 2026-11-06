from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.lint import lint


def adr(number, status=Status.ACCEPTED, supersedes=(), superseded_by=()):
    return Adr(title=f"ADR {number}", status=status, source=f"{number:04}.md", number=number, supersedes=supersedes, superseded_by=superseded_by)


def issues(*adrs):
    return sorted((i.kind, i.adr_number, i.detail) for i in lint(list(adrs)))


def test_a_clean_set_has_no_issues():
    assert issues(adr(1), adr(2, Status.SUPERSEDED, superseded_by=(3,)), adr(3, supersedes=(2,))) == []


def test_dangling_supersede_reference():
    assert issues(adr(3, supersedes=(9,))) == [("dangling-supersede-ref", 3, "supersedes ADR-9, which does not exist")]


def test_supersede_cycle():
    found = issues(adr(1, Status.SUPERSEDED, supersedes=(2,), superseded_by=(2,)), adr(2, Status.SUPERSEDED, supersedes=(1,), superseded_by=(1,)))
    assert ("supersede-cycle", 1, "ADR-1 -> ADR-2 -> ADR-1") in found


def test_status_mismatch_when_the_superseded_adr_still_says_accepted():
    assert issues(adr(2), adr(3, supersedes=(2,))) == [("status-mismatch", 2, "superseded by ADR-3 but status is accepted")]


def test_missing_status():
    assert issues(adr(4, Status.UNKNOWN)) == [("missing-status", 4, "no recognisable Status")]
