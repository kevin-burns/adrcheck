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
