"""Tracer bullet: the CLI wires real adapters end to end, with the model faked."""

import json
import subprocess
from pathlib import Path

from adrcheck.cli import main
from adrcheck.domain.verdict import Verdict
from adrcheck.ports import JudgeResponse, RawFinding

ADR = """# 1. Rows are keyed by row_key

Status: accepted
Applies to: src/**

## Decision

Every row is keyed by row_key and nothing else.
"""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "docs" / "adr").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "docs" / "adr" / "0001-row-key.md").write_text(ADR)
    (repo / "src" / "a.py").write_text("key = row_key(row)\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    (repo / "src" / "a.py").write_text('key = row["url"]\n')
    git(repo, "commit", "-q", "-am", "key by url")
    return repo


class FakeJudge:
    def compile(self, adr):
        from adrcheck.domain.obligation import Checkability, Obligation

        return (
            Obligation(
                "ADR-1/1",
                1,
                "MUST",
                "rows keyed by row_key",
                "keyed by row_key and nothing else",
                Checkability.STRUCTURAL,
                mandates=("row_key",),
            ),
        )

    def judge(self, change, cases, context):
        return JudgeResponse(
            findings=(
                RawFinding(
                    "ADR-1/1",
                    Verdict.CONFLICT,
                    "src/a.py",
                    'key = row["url"]',
                    "keyed by row_key and nothing else",
                    "keys by url",
                ),
            ),
            cost_usd=0.01,
        )


def test_check_reports_the_conflict_as_json_and_exits_zero_by_default(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    code = main(
        [
            "check",
            "--repo",
            str(repo),
            "--adr-dir",
            str(repo / "docs/adr"),
            "--range",
            "HEAD~1..HEAD",
            "--format",
            "json",
        ],
        judge=FakeJudge(),
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["findings"][0]["verdict"] == "CONFLICT" and out["findings"][0]["adr"] == 1


def test_fail_on_conflict_exits_two(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    code = main(
        [
            "check",
            "--repo",
            str(repo),
            "--adr-dir",
            str(repo / "docs/adr"),
            "--range",
            "HEAD~1..HEAD",
            "--fail-on",
            "conflict",
        ],
        judge=FakeJudge(),
    )
    assert code == 2


def test_lint_reports_hygiene_issues_without_a_model(tmp_path: Path, capsys):
    d = tmp_path / "adr"
    d.mkdir()
    (d / "0003-x.md").write_text("# 3. X\n\nStatus: accepted\nSupersedes: ADR-9\n\n## Decision\n\nx\n")
    code = main(["lint", "--adr-dir", str(d)])
    out = capsys.readouterr().out
    assert code == 1 and "dangling-supersede-ref" in out and "ADR-9" in out


def test_eval_scores_a_saved_report_against_frozen_cases_without_a_model(tmp_path: Path, capsys):
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "cases": [
                    {"commit": "abc", "adr": 2, "quote": "keyed by store.row_key", "expected": "CONFLICT"},
                    {"commit": "abc", "adr": 2, "quote": "never hidden", "expected": "COMPLIANT"},
                ]
            }
        )
    )
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {"findings": [{"commit": "abc1234", "adr": 2, "quote": "keyed by store.row_key", "verdict": "CONFLICT"}]}
        )
    )
    code = main(["eval", "--cases", str(cases), "--report", str(report)])
    out, err = capsys.readouterr()
    assert code == 0 and "2/2 hits" in err  # COMPLIANT asks for silence, so nothing raised is a hit
    assert out.splitlines()[0].startswith("hit    ADR-2 abc expected CONFLICT got CONFLICT")
    assert out.splitlines()[1].startswith("quiet  ADR-2 abc expected COMPLIANT got -")


class FailingJudge(FakeJudge):
    def judge(self, change, cases, context):
        return JudgeResponse(error="APIConnectionError: no route to host")


def test_a_run_in_which_no_case_got_a_verdict_exits_three_not_green(tmp_path: Path, capsys):
    """Operational failure is not a finding: not 0 (nothing wrong), not 2 (a conflict), but 3."""
    repo = make_repo(tmp_path)
    code = main(
        ["check", "--repo", str(repo), "--adr-dir", str(repo / "docs/adr"), "--commit", "HEAD", "--format", "json"],
        judge=FailingJudge(),
    )
    out, err = capsys.readouterr()
    assert code == 3
    assert "could not evaluate" in err and json.loads(out)["findings"][0]["verdict"] == "UNCLEAR"


class ExplodingCompiler(FakeJudge):
    def compile(self, adr):
        raise RuntimeError("provider down")


def test_a_compile_that_cannot_reach_the_model_exits_three_with_the_reason(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    code = main(
        ["check", "--repo", str(repo), "--adr-dir", str(repo / "docs/adr"), "--commit", "HEAD"],
        judge=ExplodingCompiler(),
    )
    _, err = capsys.readouterr()
    assert code == 3 and "could not evaluate" in err and "provider down" in err


def test_check_staged_judges_the_index_against_the_adrs(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    (repo / "src" / "a.py").write_text('key = row["url"]\nmore = 2\n')
    subprocess.run(["git", "-C", str(repo), "add", "src/a.py"], check=True)
    code = main(
        ["check", "--repo", str(repo), "--adr-dir", str(repo / "docs/adr"), "--staged", "--format", "json"],
        judge=FakeJudge(),
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["changes"][0]["commit"] == "STAGED"
    # HEAD already holds the cited line, so the index did not introduce it: the parent of a staged change is HEAD
    assert out["findings"][0]["verdict"] == "ADR-OVERTAKEN"


def test_write_baseline_records_the_stale_list_and_the_next_run_reports_those_rows_as_known(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)  # HEAD no longer contains row_key, so ADR-1/1 is stale
    base = ["check", "--repo", str(repo), "--adr-dir", str(repo / "docs/adr"), "--commit", "HEAD", "--format", "json"]
    code = main([*base, "--write-baseline"], judge=FakeJudge())
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["stale"] == [{"adr": 1, "obligation": "ADR-1/1", "missing": ["row_key"], "known": False}]
    written = json.loads((repo / ".adrcheck" / "baseline.json").read_text())
    assert [r["obligation"] for r in written["stale"]] == ["ADR-1/1"]

    code = main(base, judge=FakeJudge())
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["stale"][0]["known"] is True

    main([*base[:-2], "--format", "md"], judge=FakeJudge())
    md = capsys.readouterr().out
    assert "1 already in the baseline" in md and "ADR-1 ADR-1/1: missing" not in md
