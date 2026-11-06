from adrcheck.adapters.markdown_adr import parse_adr
from adrcheck.domain.adr import Status

NYGARD = """# 1. Reconciling live against intended belongs to the consumer

Date: 2026-09-18
Status: accepted
Bead: cam-vkz
Applies to: mapper/**, cli/*.py

## Context

The obvious move is to teach the mapper about Terraform.

## Decision

The mapper collects facts about what is live and exposes them. It does not read Terraform.

## Consequences

Reconciliation code lives in the consuming project.
"""


def test_nygard_header_lines_become_fields():
    adr = parse_adr(NYGARD, source="docs/adr/0001-reconciling.md")
    assert adr.number == 1
    assert adr.title == "Reconciling live against intended belongs to the consumer"
    assert adr.status is Status.ACCEPTED
    assert adr.applies_to == ("mapper/**", "cli/*.py")
    assert adr.source == "docs/adr/0001-reconciling.md"


def test_nygard_sections_are_keyed_by_canonical_name():
    adr = parse_adr(NYGARD, source="x.md")
    assert "It does not read Terraform." in adr.section("decision")
    assert "Reconciliation code lives" in adr.section("consequences")
    assert "teach the mapper" in adr.section("context")


MADR = """---
status: accepted
date: 2026-01-02
applies_to:
  - services/api/**
  - "db/*.sql"
---

# Use PostgreSQL for primary storage

## Context and Problem Statement

We need a relational store.

## Considered Options

* PostgreSQL
* MySQL

## Decision Outcome

Chosen option: PostgreSQL, because it is boring.
"""


def test_madr_front_matter_and_heading_aliases_normalise_to_the_same_adr():
    adr = parse_adr(MADR, source="docs/adr/0007-use-postgresql.md")
    assert adr.number == 7
    assert adr.status is Status.ACCEPTED
    assert adr.date == "2026-01-02"
    assert adr.applies_to == ("services/api/**", "db/*.sql")
    assert "Chosen option: PostgreSQL" in adr.section("decision")
    assert "relational store" in adr.section("context")
    assert "MySQL" in adr.section("considered options")


def test_superseded_status_records_the_successor():
    text = "# 3. Old\n\nStatus: Superseded by ADR-0005\n\n## Decision\n\nx\n"
    adr = parse_adr(text, source="0003-old.md")
    assert adr.status is Status.SUPERSEDED
    assert adr.superseded_by == (5,)


def test_supersedes_line_records_the_predecessor():
    text = "# 5. New\n\nStatus: accepted\nSupersedes: ADR-0003\n\n## Decision\n\ny\n"
    adr = parse_adr(text, source="0005-new.md")
    assert adr.supersedes == (3,)
