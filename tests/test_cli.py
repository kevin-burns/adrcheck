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
    # HEAD already holds the cited line, so the index did not touch it: the parent of a staged change is HEAD, the
    # diff is against HEAD, and a claim about an untouched line fails verification rather than becoming a verdict
    assert out["findings"][0]["verdict"] == "UNCLEAR" and "line-not-in-change" in out["findings"][0]["note"]


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


UNSCOPED_ADR = """# 2. Imports go through import_rows

Status: accepted

## Decision

Every importer calls import_rows.
"""


def test_the_scope_map_keeps_an_unscoped_adr_off_a_change_outside_its_paths(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    (repo / "docs" / "adr" / "0002-import-rows.md").write_text(UNSCOPED_ADR)
    (repo / ".adrcheck").mkdir()
    (repo / ".adrcheck" / "map.toml").write_text('[[adr]]\nid = 2\npaths = ["enrich/**"]\n')
    base = ["--repo", str(repo), "--adr-dir", str(repo / "docs/adr")]
    code = main(["check", *base, "--commit", "HEAD", "--format", "json"], judge=FakeJudge())
    out = json.loads(capsys.readouterr().out)
    excluded = {e["adr"]: e["reason"] for e in out["changes"][0]["excluded"]}
    assert code == 0 and excluded[2] == "globs did not match any changed path"

    (repo / ".adrcheck" / "map.toml").write_text('[[adr]]\nid = 1\npaths = ["lib/**"]\n')
    code = main(["lint", *base], judge=FakeJudge())
    assert code == 1 and "scope-disagreement\tADR-1\t" in capsys.readouterr().out


def test_a_compile_that_cannot_reach_the_model_exits_three_from_the_compile_command_too(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    code = main(["compile", "--repo", str(repo), "--adr-dir", str(repo / "docs/adr")], judge=ExplodingCompiler())
    err = capsys.readouterr().err
    assert code == 3 and "could not compile ADR-1: RuntimeError: provider down" in err


def test_the_compile_seat_can_run_on_a_different_provider_than_the_judge_seat(monkeypatch):
    from adrcheck.adapters.claude_cli import ClaudeCliRunner
    from adrcheck.adapters.openai_compat import OpenAICompatRunner
    from adrcheck.cli import _seats

    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    compiler, judge = _seats(model="claude-cli:sonnet", compile_model="ollama:qwen3.5:9b-q8_0")
    assert isinstance(compiler.runner, OpenAICompatRunner) and compiler.runner.model == "qwen3.5:9b-q8_0"
    assert isinstance(judge.runner, ClaudeCliRunner) and judge.runner.model == "sonnet"
    compiler, judge = _seats(model="claude-cli:sonnet", compile_model=None)
    assert compiler is judge


def test_eval_run_executes_the_corpus_commits_writes_the_report_and_scores_it(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    head = git(repo, "rev-parse", "HEAD").strip()
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "corpus": "t",
                "repo": str(repo),
                "adr_dir": "docs/adr",
                "commits": [head[:7]],
                "cases": [
                    {"commit": head[:7], "adr": 1, "quote": "keyed by row_key and nothing else", "expected": "CONFLICT"}
                ],
            }
        )
    )
    report = tmp_path / "out.json"
    code = main(["eval", "--cases", str(cases), "--run", "--report", str(report)], judge=FakeJudge())
    out, err = capsys.readouterr()
    assert code == 0 and "1/1 hits" in err and out.startswith("hit")
    assert json.loads(report.read_text())["findings"][0]["verdict"] == "CONFLICT"


def test_eval_run_reads_the_adrs_at_the_frozen_ref_when_the_corpus_says_so(tmp_path: Path, capsys, monkeypatch):
    repo = make_repo(tmp_path)
    head = git(repo, "rev-parse", "HEAD").strip()
    (repo / "docs" / "adr" / "0001-row-key.md").write_text(ADR.replace("accepted", "deprecated"))
    git(repo, "commit", "-q", "-am", "deprecate")
    monkeypatch.setenv("ADRCHECK_EVAL_T_REPO", str(repo))
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "corpus": "t",
                "repo_env": "ADRCHECK_EVAL_T_REPO",
                "adrs_at": head[:7],
                "cases": [
                    {"commit": head[:7], "adr": 1, "quote": "keyed by row_key and nothing else", "expected": "CONFLICT"}
                ],
            }
        )
    )
    code = main(["eval", "--cases", str(cases), "--run", "--report", str(tmp_path / "o.json")], judge=FakeJudge())
    assert (
        code == 0 and "1/1 hits" in capsys.readouterr().err
    )  # the working tree says deprecated; the ref says accepted


def test_check_max_calls_caps_the_judge_and_says_which_commits_were_not_judged(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)
    (repo / "src" / "a.py").write_text('key = row["url"]\nmore = 2\n')
    git(repo, "commit", "-q", "-am", "more")
    code = main(
        [
            "check",
            "--repo",
            str(repo),
            "--adr-dir",
            str(repo / "docs/adr"),
            "--range",
            "HEAD~2..HEAD",
            "--max-calls",
            "1",
            "--format",
            "json",
        ],
        judge=FakeJudge(),
    )
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert code == 0
    assert [c["judge_calls"] for c in out["changes"]] == [1, 0]
    assert out["changes"][1]["problems"] == ["judge call budget of 1 reached; 1 ADR not judged for this change"]
    assert "1 change(s) not judged: --max-calls 1 reached" in captured.err


def test_explain_prints_one_adr_with_where_each_anchor_lives(tmp_path: Path, capsys):
    repo = make_repo(tmp_path)  # HEAD has key = row["url"]; row_key is gone
    code = main(["explain", "--repo", str(repo), "--adr-dir", str(repo / "docs/adr"), "--adr", "1"], judge=FakeJudge())
    out = capsys.readouterr().out
    assert code == 0
    assert "ADR-1" in out and "ADR-1/1" in out
    assert "row_key" in out and "missing" in out
    assert "stale" in out.lower()
