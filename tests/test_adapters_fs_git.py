import os
import subprocess
from pathlib import Path

from adrcheck.adapters.git_changes import GitChanges, GitRepo
from adrcheck.adapters.markdown_adr_source import MarkdownAdrSource
from adrcheck.domain.adr import Status


def test_markdown_source_reads_every_numbered_adr_in_the_directory(tmp_path: Path):
    d = tmp_path / "docs" / "adr"
    d.mkdir(parents=True)
    (d / "0001-first.md").write_text("# 1. First\n\nStatus: accepted\n\n## Decision\n\na\n")
    (d / "0002-second.md").write_text("# 2. Second\n\nStatus: proposed\n\n## Decision\n\nb\n")
    (d / "README.md").write_text("# index\n")
    adrs = MarkdownAdrSource(d).adrs()
    assert [(a.number, a.status) for a in adrs] == [(1, Status.ACCEPTED), (2, Status.PROPOSED)]
    assert adrs[0].source.endswith("docs/adr/0001-first.md")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text("key = row_key(row)\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    (repo / "a.py").write_text('key = row["url"]\n')
    git(repo, "commit", "-q", "-am", "second\n\nAdr-Exception: ADR-2 because\n")
    return repo


def test_git_changes_yields_one_change_per_commit_with_parent_and_message(tmp_path: Path):
    repo = make_repo(tmp_path)
    changes = GitChanges(repo).changes("HEAD~1..HEAD")
    [c] = changes
    assert c.message.startswith("second")
    assert "Adr-Exception: ADR-2 because" in c.message
    assert c.parent == git(repo, "rev-parse", "HEAD~1").strip()
    assert [line.text for line in c.files[0].added] == ['key = row["url"]']
    assert [line.text for line in c.files[0].removed] == ["key = row_key(row)"]


def test_git_repo_probes_whether_a_needle_occurs_anywhere_at_a_ref(tmp_path: Path):
    repo = make_repo(tmp_path)
    r = GitRepo(repo)
    parent = git(repo, "rev-parse", "HEAD~1").strip()
    assert r.contains(parent, "row_key") is True
    assert r.contains(parent, 'row["url"]') is False
    assert r.read("HEAD", "a.py") == 'key = row["url"]\n'


def test_contains_ignores_comments_docstrings_and_prose_files(tmp_path: Path):
    repo = tmp_path / "r2"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text(
        '"""An earlier import_rows() was removed."""\n# import_rows is gone\nx = cached_rows()\n'
    )
    (repo / "notes.md").write_text("import_rows was the importer\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    r = GitRepo(repo)
    assert r.contains("HEAD", "import_rows") is False
    assert r.contains("HEAD", "cached_rows") is True


def test_contains_still_sees_string_literals_and_non_python_code(tmp_path: Path):
    repo = tmp_path / "r3"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "c.py").write_text('cfg = {"exclude_company": []}\n')
    (repo / "run.sh").write_text("li-assist jobs get\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    r = GitRepo(repo)
    assert r.contains("HEAD", "exclude_company") is True
    assert r.contains("HEAD", "li-assist") is True


def test_strip_python_prose_keeps_code_spacing_intact():
    from adrcheck.adapters.git_changes import strip_python_prose

    src = '"""doc"""\nkey = store.row_key(row)  # comment\n'
    out = strip_python_prose(src)
    assert "store.row_key(row)" in out and "doc" not in out and "comment" not in out


def test_contains_probes_file_paths_as_well_as_contents(tmp_path: Path):
    repo = tmp_path / "r4"
    (repo / "enrich").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "enrich" / "decide.py").write_text("x = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    r = GitRepo(repo)
    assert r.contains("HEAD", "decide.py") is True
    assert r.contains("HEAD", "enrich/decide.py") is True
    assert r.contains("HEAD", "enrich/linkedin.py") is False


def test_staged_is_one_change_from_the_index_with_head_as_parent(tmp_path: Path):
    """Pre-commit sees the index, not a commit: the staged diff, HEAD as parent, the prepared message if any."""
    repo = make_repo(tmp_path)
    (repo / "a.py").write_text('key = row["url"]\nextra = 1\n')
    (repo / "b.py").write_text("print('new')\n")
    git(repo, "add", "a.py", "b.py")
    msg = repo / ".git" / "COMMIT_EDITMSG"
    msg.write_text("wip: add extra\n\nAdr-Exception: ADR-2 reason\n")
    head_time = int(git(repo, "log", "-1", "--format=%ct").strip())
    os.utime(msg, (head_time + 10, head_time + 10))  # written after HEAD: a message prepared for this commit
    change = GitChanges(repo).staged()
    assert change.ref == "STAGED" and change.parent == git(repo, "rev-parse", "HEAD").strip()
    assert sorted(change.paths()) == ["a.py", "b.py"]
    assert change.touched("a.py", "extra = 1", kinds=("+",)) and "Adr-Exception: ADR-2 reason" in change.message
    # the post-image of a staged file is the index content, and the probe reads the index too
    assert GitRepo(repo).read("STAGED", "b.py") == "print('new')\n"
    assert GitRepo(repo).contains("STAGED", "extra = 1") is True
    assert GitRepo(repo).contains("HEAD", "extra = 1") is False


def test_the_adr_directory_is_discovered_at_the_common_paths_when_none_is_given(tmp_path: Path):
    from adrcheck.adapters.markdown_adr_source import discover_adr_dir

    assert discover_adr_dir(tmp_path) is None
    (tmp_path / "docs" / "architecture" / "decisions").mkdir(parents=True)
    assert discover_adr_dir(tmp_path) == tmp_path / "docs" / "architecture" / "decisions"
    (tmp_path / "docs" / "adr").mkdir()
    assert discover_adr_dir(tmp_path) == tmp_path / "docs" / "adr"  # the most specific conventional name wins


def test_a_binary_file_in_the_tree_does_not_break_the_probe_or_the_post_image(tmp_path: Path):
    """Seen on the first public corpus: one undecodable blob and the whole run died with exit 3."""
    repo = make_repo(tmp_path)
    (repo / "logo.ico").write_bytes(b"\x00\x00\x01\x00\xa8\xff\xfe binary")
    (repo / "b.py").write_text("needle_in_code = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "binary")
    assert GitRepo(repo).contains("HEAD", "needle_in_code") is True
    assert "binary" in GitRepo(repo).read("HEAD", "logo.ico")


def test_occurrences_counts_whole_identifiers_in_code_so_a_definition_alone_is_one(tmp_path: Path):
    repo = make_repo(tmp_path)
    (repo / "lib.py").write_text("def import_rows(rows):\n    return rows\n\ndef fetch(): pass\n")
    (repo / "b.py").write_text("from lib import fetch\nfetch()\n# import_rows mentioned in a comment only\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "third")
    r = GitRepo(repo)
    assert r.occurrences("HEAD", "import_rows") == 1  # the def; the comment is stripped, 'rows' is not a match
    assert r.occurrences("HEAD", "fetch") == 3
    assert r.occurrences("HEAD", "nothing_here") == 0
    assert r.occurrences("no-such-ref", "fetch") is None


def test_adrs_at_reads_the_adr_directory_as_it_stood_at_a_ref(tmp_path: Path):
    from adrcheck.adapters.markdown_adr_source import adrs_at

    repo = make_repo(tmp_path)
    (repo / "docs" / "adr").mkdir(parents=True)
    (repo / "docs" / "adr" / "0001-key.md").write_text("# 1. Key\n\nStatus: accepted\n\n## Decision\n\nOld text.\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "adr v1")
    frozen = git(repo, "rev-parse", "HEAD").strip()
    (repo / "docs" / "adr" / "0001-key.md").write_text("# 1. Key\n\nStatus: deprecated\n\n## Decision\n\nNew text.\n")
    git(repo, "commit", "-q", "-am", "adr v2")
    [adr] = adrs_at(GitRepo(repo), frozen, "docs/adr")
    assert adr.number == 1 and adr.status.value == "accepted" and adr.section("decision") == "Old text."
    assert adr.blob == git(repo, "rev-parse", f"{frozen}:docs/adr/0001-key.md").strip()
    assert adrs_at(GitRepo(repo), frozen, "no/such/dir") == []


def test_locate_names_the_code_files_that_hold_an_anchor_and_a_path_locates_itself(tmp_path: Path):
    repo = make_repo(tmp_path)
    (repo / "lib.py").write_text("def import_rows(rows):\n    return rows\n\ndef fetch(): pass\n")
    (repo / "b.py").write_text("from lib import fetch\nfetch()\n# import_rows mentioned in a comment only\n")
    (repo / "notes.md").write_text("fetch is described here\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "third")
    r = GitRepo(repo)
    assert r.locate("HEAD", "fetch") == ["b.py", "lib.py"]  # prose file skipped, sorted
    assert r.locate("HEAD", "import_rows") == ["lib.py"]  # the comment in b.py is stripped
    assert r.locate("HEAD", "lib.py") == ["lib.py"]  # a path anchor locates itself
    assert r.locate("HEAD", "nothing_here") == []
    assert r.locate("no-such-ref", "fetch") is None


def test_the_committed_obligation_cache_is_not_code_so_an_anchor_named_only_there_is_missing(tmp_path: Path):
    """A repository that commits .adrcheck/obligations/ holds every anchor string in those files. Counting them as
    code would make the stale sweep blind to its own ADRs; seen on adrcheck itself via `explain`."""
    repo = make_repo(tmp_path)
    (repo / ".adrcheck" / "obligations").mkdir(parents=True)
    (repo / ".adrcheck" / "obligations" / "abc.json").write_text('[{"mandates": ["import_rows"]}]\n')
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "cache")
    r = GitRepo(repo)
    assert r.contains("HEAD", "import_rows") is False
    assert r.locate("HEAD", "import_rows") == []
    assert r.occurrences("HEAD", "import_rows") == 0


ADR_BODY = "\n\nStatus: Accepted\n\n## Decision\n\nWe do X.\n"


def test_the_source_reads_every_markdown_record_whatever_the_filename_shape_and_skips_the_non_records(tmp_path: Path):
    """Kevin 2026-11-09: 'what if we have ADR-001 as the key?' The old filter read only names starting with digits,
    so ADR-001-*.md was skipped silently. Now every .md is a record unless it is the directory's README, index
    or template; the number comes from the title first, then the filename, and a date prefix is not a number."""
    d = tmp_path / "adr"
    d.mkdir()
    (d / "0001-use-postgres.md").write_text("# 1. Use Postgres" + ADR_BODY)
    (d / "ADR-002-use-redis.md").write_text("# Use Redis" + ADR_BODY)
    (d / "adr_003_use_kafka.md").write_text("# Use Kafka" + ADR_BODY)
    (d / "20220819-use-log4brains.md").write_text("# Use Log4brains" + ADR_BODY)
    (d / "2026-01-10-use-sqlite.md").write_text("# [ADR-5] Use SQLite" + ADR_BODY)
    (d / "no-number-at-all.md").write_text("# Use Nothing" + ADR_BODY)
    (d / "README.md").write_text("# Architecture decision records\n\nAn index.\n")
    (d / "index.md").write_text("# Index\n")
    (d / "template.md").write_text("# NUMBER. TITLE" + ADR_BODY)
    (d / "notes.txt").write_text("not markdown")
    adrs = {Path(a.source).name: a for a in MarkdownAdrSource(d).adrs()}
    assert set(adrs) == {
        "0001-use-postgres.md",
        "ADR-002-use-redis.md",
        "adr_003_use_kafka.md",
        "20220819-use-log4brains.md",
        "2026-01-10-use-sqlite.md",
        "no-number-at-all.md",
    }
    assert adrs["0001-use-postgres.md"].number == 1
    assert adrs["ADR-002-use-redis.md"].number == 2
    assert adrs["adr_003_use_kafka.md"].number == 3
    assert adrs["20220819-use-log4brains.md"].number is None  # a date, not a number
    assert adrs["2026-01-10-use-sqlite.md"].number == 5  # the title's [ADR-5] wins over the date prefix
    assert adrs["no-number-at-all.md"].number is None


def test_combined_judges_a_range_as_the_one_change_it_merges(tmp_path: Path):
    """A pull request is judged as what it merges (ADR-13): one Change whose parent is the base, whose files are the
    net diff, and whose message carries every commit's message so an Adr-Exception trailer on any of them counts.
    A line added in one commit and removed in a later one is not in the change at all."""
    repo = make_repo(tmp_path)
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "a.py").write_text('key = row["url"]\nbad = import_db()\n')
    git(repo, "commit", "-q", "-am", "first: adds a bad line")
    (repo / "a.py").write_text('key = row["url"]\ngood = 1\n')
    git(repo, "commit", "-q", "-am", "second: repairs it\n\nAdr-Exception: ADR-1 deliberate, see the thread")
    head = git(repo, "rev-parse", "HEAD").strip()
    one = GitChanges(repo).combined(f"{base}..{head}")
    assert one.parent == base and one.ref == head
    assert "first: adds a bad line" in one.message and "Adr-Exception: ADR-1" in one.message
    added = [ln.text for f in one.files for ln in f.added]
    assert added == ["good = 1"]  # bad = import_db() was added then removed: not part of what merges


def test_occurrences_counts_code_not_file_paths_so_a_module_named_after_its_function_is_still_dead(tmp_path: Path):
    """planted-large: retry() lives in orders/infra/retry.py and nothing calls it. The path listing is part of the
    code text for contains() so an ADR may name a module, but it must not count as a use of the identifier."""
    repo = make_repo(tmp_path)
    (repo / "retry.py").write_text("def retry(fn):\n    return fn()\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "third")
    r = GitRepo(repo)
    assert r.occurrences("HEAD", "retry") == 1  # the definition; retry.py in the listing is not a call
    assert r.contains("HEAD", "retry.py") is True  # the path is still present for the stale sweep


def test_a_commit_editmsg_older_than_head_is_the_previous_commits_message_and_is_not_read(tmp_path: Path):
    """The pre-commit hook runs before git writes the new message, so .git/COMMIT_EDITMSG still holds the previous
    commit's text. Reading it would carry an Adr-Exception forward to a change it was never written for (ADR-6
    says the waiver is per commit). Only a file newer than HEAD counts."""
    repo = make_repo(tmp_path)  # HEAD's own message carried "Adr-Exception: ADR-2 because"
    (repo / "a.py").write_text('key = row["url"]\nextra = 1\n')
    git(repo, "add", "a.py")
    msg = repo / ".git" / "COMMIT_EDITMSG"
    msg.write_text("second\n\nAdr-Exception: ADR-2 because\n")
    head_time = int(git(repo, "log", "-1", "--format=%ct").strip())
    os.utime(msg, (head_time - 10, head_time - 10))
    assert GitChanges(repo).staged().message == ""


def test_has_line_matches_a_whole_line_so_an_alias_import_or_a_string_mention_is_not_a_precedent(tmp_path: Path):
    """planted-large 7e9b995: `import requests` was called already-present because contains() found it inside
    `import requests as http` and inside a log string. A precedent is the same line, not the same substring."""
    repo = make_repo(tmp_path)
    (repo / "w.py").write_text("import requests as http\nlog.info('import requests is not allowed here')\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "third")
    r = GitRepo(repo)
    assert r.has_line("HEAD", "import requests") is False
    assert r.has_line("HEAD", "import requests as http") is True
    assert r.has_line("HEAD", "  import requests as http  ") is True  # surrounding whitespace does not matter
    assert r.has_line("no-such-ref", "x") is None


def test_the_working_tree_source_records_the_blob_id_git_would_give_the_file(tmp_path: Path):
    from adrcheck.adapters.markdown_adr_source import MarkdownAdrSource

    repo = make_repo(tmp_path)
    (repo / "docs" / "adr").mkdir(parents=True)
    (repo / "docs" / "adr" / "0001-key.md").write_text("# 1. Key\n\nStatus: accepted\n\n## Decision\n\nText.\n")
    [adr] = MarkdownAdrSource(repo / "docs" / "adr").adrs()
    assert adr.blob == git(repo, "hash-object", "docs/adr/0001-key.md").strip()
