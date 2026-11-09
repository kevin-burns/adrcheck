# 12. Every markdown file in the ADR directory is a record; the number comes from the title, then the filename

Date: 2026-11-09
Status: Accepted
Applies to: src/adrcheck/adapters/markdown_adr_source.py, src/adrcheck/adapters/markdown_adr.py, src/adrcheck/domain/lint.py

## Context

Teams name ADR files in several ways: `0001-title.md` (Nygard, MADR, adr-tools), `ADR-001-title.md` and
`adr_001_title.md` (house styles), `20220819-title.md` (Log4brains, a date slug), `2026-01-10-title.md`,
and sometimes a bare `title.md` with the number in the heading. Until 2026-11-09 the source adapter read
only files whose names began with a digit, so `ADR-001-title.md` was skipped without a word, and a date
slug became ADR number 20220819. Kevin asked what would happen with `ADR-001` as the key; the probe that
answered him found both faults. A record that is silently not read is worse than one that is read and
reported.

## Decision

`MarkdownAdrSource` and `adrs_at()` in `src/adrcheck/adapters/markdown_adr_source.py` read every `.md`
file in the ADR directory except the directory's own `README`, `index` and `template`, decided by
`is_record()`. `parse_adr()` in `src/adrcheck/adapters/markdown_adr.py` takes the number from the title
first, in any of the shapes `# 1. Title`, `# ADR-001: Title`, `# ADR 001 Title`, `# [ADR-001] Title` and
`# 001 - Title`, and otherwise from the filename through `filename_number()`, which accepts a leading
number with or without an `ADR` prefix and treats a leading date, eight digits or `yyyy-mm-dd`, as not a
number. A record with no number from either source is kept with `number` None, and `lint` reports it as
`missing-number`, because nothing can supersede, depend on or waive a record that cannot be named.

## Consequences

A misnamed file is a lint finding, not a silent gap. Leading zeros do not matter: `ADR-001`, `0001` and
`1` are the same record, and references in text resolve the same way. Two files that resolve to one number
are still `duplicate-number`. A team that keeps a template in the ADR directory under another name gets a
`missing-number` or `missing-status` finding for it and renames it; that is the intended nudge. The
filename is never the only truth: a title number wins over a filename number when both exist and differ,
which is also when a human should look.
