"""One decision in every ADR shape must bind on roles, not headings. No model: parse and verify() only."""

from pathlib import Path

import pytest

from adrcheck.adapters.markdown_adr import parse_adr
from adrcheck.domain.adr import Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.verify import BINDING_SECTIONS, Claim, verify

CORPUS = Path(__file__).parent / "fixtures" / "adr-templates"
TEMPLATES = sorted(p.name for p in CORPUS.iterdir() if p.is_dir())
HAS_REJECTED = {"madr-4", "tyree-akerman", "arc42-s9", "business-case", "itd", "bold-labels", "table", "y-statement"}
HAS_CONSEQUENCES = set(TEMPLATES) - {"planguage"}

BINDING_SENTENCE = "folded, not dropped"
REJECTED_SENTENCE = "Drop rows the triage says no to"


def load(template: str):
    [path] = (CORPUS / template).glob("*.md")
    return parse_adr(path.read_text(), source=str(path))


@pytest.mark.parametrize("template", TEMPLATES)
def test_status_is_accepted_in_every_shape(template):
    assert load(template).status is Status.ACCEPTED, template


@pytest.mark.parametrize("template", TEMPLATES)
def test_the_binding_role_is_found_and_holds_the_decision_sentence(template):
    adr = load(template)
    assert BINDING_SENTENCE in adr.section("decision"), (template, dict(adr.sections))


@pytest.mark.parametrize("template", sorted(HAS_CONSEQUENCES))
def test_consequences_land_in_the_consequences_role(template):
    assert (
        "never hidden" in load(template).section("consequences")
        or "storage grows" in load(template).section("consequences").lower()
    ), template


@pytest.mark.parametrize("template", sorted(HAS_REJECTED))
def test_a_quote_from_the_rejected_role_is_refused_by_verify(template):
    adr = load(template)
    assert REJECTED_SENTENCE.lower() in adr.section("options").lower(), (template, dict(adr.sections))
    change = Change(
        ref="c1",
        parent="c0",
        message="m",
        files=(FileChange("enrich/x.py", "enrich/x.py", added=(Line("enrich/x.py", "+", 1, "drop(row)"),)),),
    )
    result = verify(
        Claim(adr_number=2, path="enrich/x.py", line_text="drop(row)", quote=REJECTED_SENTENCE), change, adr
    )
    assert "quote-outside-decision" in result.failed, template


@pytest.mark.parametrize("template", sorted(set(TEMPLATES) - HAS_REJECTED))
def test_shapes_without_a_rejected_role_report_none_rather_than_guessing(template):
    adr = load(template)
    assert adr.section("options") == "", template
    assert "options" in adr.missing_roles(), template


def test_binding_sections_are_still_exactly_decision_and_consequences():
    assert BINDING_SECTIONS == ("decision", "consequences")
