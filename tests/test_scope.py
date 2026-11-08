"""A repo-side scope map for ADRs whose text cannot carry an Applies to header."""

from pathlib import Path

from adrcheck.adapters.scope_map import load_scope_map
from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.scope import scope


def adr(number, applies_to=()):
    return Adr(
        title=f"ADR {number}", status=Status.ACCEPTED, source=f"{number:04}.md", number=number, applies_to=applies_to
    )


def test_the_map_scopes_an_adr_that_has_no_header_and_leaves_a_header_alone():
    scoped, issues = scope([adr(4), adr(5, ("a/**",))], {4: ("enrich/**", "cli.py"), 5: ("a/**",)})
    assert [a.applies_to for a in scoped] == [("enrich/**", "cli.py"), ("a/**",)] and issues == ()


def test_a_header_wins_over_the_map_and_the_disagreement_is_a_hygiene_issue():
    scoped, issues = scope([adr(5, ("a/**",))], {5: ("b/**",)})
    assert scoped[0].applies_to == ("a/**",)
    assert [(i.kind, i.adr_number) for i in issues] == [("scope-disagreement", 5)]
    assert "header a/** wins over map b/**" in issues[0].detail


def test_a_map_entry_for_an_adr_that_does_not_exist_is_a_hygiene_issue():
    _, issues = scope([adr(4)], {9: ("x/**",)})
    assert [(i.kind, i.adr_number, i.detail) for i in issues] == [
        ("map-unknown-adr", 9, "map names ADR-9, which does not exist")
    ]


def test_the_toml_map_is_read_and_a_missing_file_is_an_empty_map(tmp_path: Path):
    path = tmp_path / "map.toml"
    path.write_text(
        '[[adr]]\nid = 4\npaths = ["enrich/linkedin.py", "enrich/**"]\n\n[[adr]]\nid = 7\npaths = ["cli.py"]\n'
    )
    assert load_scope_map(path) == {4: ("enrich/linkedin.py", "enrich/**"), 7: ("cli.py",)}
    assert load_scope_map(tmp_path / "none.toml") == {}
