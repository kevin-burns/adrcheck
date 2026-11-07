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
