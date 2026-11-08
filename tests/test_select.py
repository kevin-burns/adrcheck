from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.select import select


def adr(number, status=Status.ACCEPTED, applies_to=()):
    return Adr(title=f"ADR {number}", status=status, source=f"{number:04}.md", number=number, applies_to=applies_to)


def change(*paths, message="msg", added_text=()):
    files = tuple(
        FileChange(
            path=p,
            old_path=p,
            added=tuple(Line(path=p, kind="+", number=i + 1, text=t) for i, t in enumerate(added_text)),
        )
        for p in paths
    )
    return Change(ref="c1", message=message, files=files)


def test_glob_on_applies_to_selects_and_names_the_signal():
    result = select([adr(1, applies_to=("enrich/**",))], change("enrich/store.py"))
    assert [(s.adr.number, s.signals) for s in result.selected] == [(1, frozenset({"glob"}))]


def test_an_adr_id_in_the_commit_message_or_a_changed_line_selects_by_reference():
    adrs = [adr(2, applies_to=("bin/**",)), adr(3, applies_to=("bin/**",))]
    result = select(adrs, change("enrich/x.py", message="see ADR-0002", added_text=("# per adr 3",)))
    assert sorted((s.adr.number, s.signals) for s in result.selected) == [
        (2, frozenset({"ref"})),
        (3, frozenset({"ref"})),
    ]


def test_scoped_adr_whose_globs_miss_is_excluded_with_a_reason():
    result = select([adr(1, applies_to=("bin/**",))], change("enrich/store.py"))
    assert result.selected == ()
    assert [(e.adr.number, e.reason) for e in result.excluded] == [(1, "globs did not match any changed path")]


def test_unscoped_accepted_adr_is_left_for_the_model_to_decide():
    result = select([adr(1)], change("enrich/store.py"))
    assert [s.adr.number for s in result.undetermined] == [1]


def test_only_accepted_adrs_are_considered():
    adrs = [adr(1, Status.PROPOSED, ("enrich/**",)), adr(2, Status.SUPERSEDED, ("enrich/**",)), adr(3, Status.REJECTED)]
    result = select(adrs, change("enrich/store.py"))
    assert result.selected == () and result.undetermined == ()
    assert sorted(e.reason for e in result.excluded) == [
        "status is proposed; this change touches its paths, not enforced",
        "status is rejected",
        "status is superseded",
    ]


def test_a_reference_in_prose_or_data_does_not_select():
    """A spike note or a cache entry naming ADR-4 is not code that could break ADR-4; judging it costs money for nothing."""
    adrs = [adr(4, applies_to=("src/**",)), adr(5, applies_to=("src/**",))]
    prose = change("docs/spikes/run.md", added_text=("| 659695c | ADR-4/2 | COMPLIANT |",))
    data = change(".adrcheck/obligations/abc.json", added_text=('"id": "ADR-5/1",',))
    assert select(adrs, prose).selected == ()
    assert select(adrs, data).selected == ()
    code = change("lib/x.py", added_text=("# per ADR-4",))
    assert [s.adr.number for s in select(adrs, code).selected] == [4]


def test_a_proposed_adr_whose_paths_are_touched_is_excluded_with_a_notice_not_silently():
    result = select([adr(7, Status.PROPOSED, applies_to=("enrich/**",))], change("enrich/store.py"))
    assert [(e.adr.number, e.reason) for e in result.excluded] == [
        (7, "status is proposed; this change touches its paths, not enforced")
    ]
    # the same ADR off its paths keeps the plain reason
    off = select([adr(7, Status.PROPOSED, applies_to=("enrich/**",))], change("bin/x.py"))
    assert [e.reason for e in off.excluded] == ["status is proposed"]
