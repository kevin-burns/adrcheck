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
    (repo / ".git" / "COMMIT_EDITMSG").write_text("wip: add extra\n\nAdr-Exception: ADR-2 reason\n")
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
    assert adrs_at(GitRepo(repo), frozen, "no/such/dir") == []
