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
    assert "MySQL" in adr.section("options")  # the rejected role, whatever the heading said


def test_superseded_status_records_the_successor():
    text = "# 3. Old\n\nStatus: Superseded by ADR-0005\n\n## Decision\n\nx\n"
    adr = parse_adr(text, source="0003-old.md")
    assert adr.status is Status.SUPERSEDED
    assert adr.superseded_by == (5,)


def test_supersedes_line_records_the_predecessor():
    text = "# 5. New\n\nStatus: accepted\nSupersedes: ADR-0003\n\n## Decision\n\ny\n"
    adr = parse_adr(text, source="0005-new.md")
    assert adr.supersedes == (3,)


LINKED = """# 4. Exports go through the importer

Status: Accepted
Depends on: ADR-2, ADR-3
Applies to: ingest/**

## Context

See the [design note](../design.md) and [ADR-2](0002-keys.md); the spec is at https://example.invalid/spec
and the section below is [local](#consequences).

## Decision

Every CSV read goes through `import_rows()`.

## Consequences

One place to add validation.
"""


def test_a_depends_on_header_records_the_dependencies_and_relative_links_are_kept_for_lint():
    adr = parse_adr(LINKED, source="docs/adr/0004-exports.md")
    assert adr.depends_on == (2, 3)
    # relative file links only: an absolute URL and a same-page anchor are not local files to resolve
    assert adr.links == ("../design.md", "0002-keys.md")


def test_title_shapes_with_the_number_in_brackets_or_before_a_dash_give_a_clean_number_and_title():
    body = "\n\nStatus: Accepted\n\n## Decision\n\nWe do X.\n"
    a = parse_adr("# [ADR-001] Use Postgres" + body, source="x.md")
    assert (a.number, a.title) == (1, "Use Postgres")
    a = parse_adr("# 001 - Use Postgres" + body, source="x.md")
    assert (a.number, a.title) == (1, "Use Postgres")
    a = parse_adr("# ADR 001 Use Postgres" + body, source="x.md")
    assert (a.number, a.title) == (1, "Use Postgres")
    a = parse_adr("# ADR-0007: Use Postgres" + body, source="x.md")
    assert (a.number, a.title) == (7, "Use Postgres")


def test_a_date_prefixed_filename_is_not_a_number_but_an_adr_prefixed_one_is():
    body = "# Use Postgres\n\nStatus: Accepted\n\n## Decision\n\nWe do X.\n"
    assert parse_adr(body, source="docs/adr/20220819-use-postgres.md").number is None
    assert parse_adr(body, source="docs/adr/2026-01-10-use-postgres.md").number is None
    assert parse_adr(body, source="docs/adr/ADR-0012-use-postgres.md").number == 12
    assert parse_adr(body, source="docs/adr/adr_12_use_postgres.md").number == 12
    assert parse_adr(body, source="docs/adr/0012-use-postgres.md").number == 12
    assert parse_adr(body, source="docs/adr/12.md").number == 12
