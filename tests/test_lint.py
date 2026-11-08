from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.lint import lint


def adr(number, status=Status.ACCEPTED, supersedes=(), superseded_by=(), sections=None):
    return Adr(
        title=f"ADR {number}",
        status=status,
        source=f"{number:04}.md",
        number=number,
        supersedes=supersedes,
        superseded_by=superseded_by,
        sections={"decision": "d"} if sections is None else sections,
    )


def issues(*adrs):
    return sorted((i.kind, i.adr_number, i.detail) for i in lint(list(adrs)))


def test_a_clean_set_has_no_issues():
    assert issues(adr(1), adr(2, Status.SUPERSEDED, superseded_by=(3,)), adr(3, supersedes=(2,))) == []


def test_dangling_supersede_reference():
    assert issues(adr(3, supersedes=(9,))) == [("dangling-supersede-ref", 3, "supersedes ADR-9, which does not exist")]


def test_supersede_cycle():
    found = issues(
        adr(1, Status.SUPERSEDED, supersedes=(2,), superseded_by=(2,)),
        adr(2, Status.SUPERSEDED, supersedes=(1,), superseded_by=(1,)),
    )
    assert ("supersede-cycle", 1, "ADR-1 -> ADR-2 -> ADR-1") in found


def test_status_mismatch_when_the_superseded_adr_still_says_accepted():
    assert issues(adr(2), adr(3, supersedes=(2,))) == [
        ("status-mismatch", 2, "superseded by ADR-3 but status is accepted")
    ]


def test_missing_status():
    assert issues(adr(4, Status.UNKNOWN)) == [("missing-status", 4, "no recognisable Status")]


def test_an_accepted_adr_with_no_binding_role_is_reported_not_guessed():
    """A shape the parser could not bind on compiles to nothing; say so instead of letting it pass silently."""
    assert issues(adr(4, sections={"context": "why", "options": "a or b"})) == [
        ("no-binding-section", 4, "no decision or consequences section found; nothing binds")
    ]
    assert issues(adr(5, Status.PROPOSED, sections={})) == []


def test_two_adrs_sharing_a_number_are_reported_once_per_pair():
    """Seen in the wild (two 0007 files in one directory): every reference to ADR-7 is then ambiguous."""
    a, b = adr(7), adr(7)
    found = issues(a, b, adr(8))
    assert found == [("duplicate-number", 7, "two records share number 7: 0007.md and 0007.md")]


def test_an_adr_that_names_itself_as_successor_or_predecessor_is_a_self_supersede():
    assert issues(adr(4, Status.SUPERSEDED, superseded_by=(4,))) == [("self-supersede", 4, "ADR-4 supersedes itself")]
    assert ("self-supersede", 5, "ADR-5 supersedes itself") in issues(adr(5, supersedes=(5,)))


def test_more_than_one_distinct_successor_is_reported():
    got = issues(adr(2, Status.SUPERSEDED, superseded_by=(3, 4)), adr(3, supersedes=(2,)), adr(4, supersedes=(2,)))
    assert ("multiple-supersede-targets", 2, "superseded by ADR-3 and ADR-4; one decision has one successor") in got


def test_a_proposed_successor_may_declare_supersedes_while_the_predecessor_stays_accepted():
    # a pending proposal, not a status mismatch: the old decision still holds until the new one is accepted
    assert issues(adr(1), adr(2, Status.PROPOSED, supersedes=(1,))) == []
    # once the successor is accepted the predecessor must say so
    assert issues(adr(1), adr(2, supersedes=(1,))) == [
        ("status-mismatch", 1, "superseded by ADR-2 but status is accepted")
    ]
