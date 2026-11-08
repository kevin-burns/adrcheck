"""Composition root. Parses flags, wires adapters to use cases, renders. No logic of its own."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from adrcheck.adapters.baseline_file import load_baseline, write_baseline
from adrcheck.adapters.eval_cases import load_cases
from adrcheck.adapters.git_changes import GitChanges
from adrcheck.adapters.markdown_adr_source import MarkdownAdrSource, adrs_at, discover_adr_dir
from adrcheck.adapters.obligation_cache import CachedCompiler
from adrcheck.adapters.providers import runner_for
from adrcheck.adapters.render import to_json, to_markdown
from adrcheck.adapters.scope_map import load_scope_map
from adrcheck.chatmodel import PROMPT_VERSION, ChatModelSeats
from adrcheck.domain.lint import lint
from adrcheck.domain.scope import scope
from adrcheck.domain.verdict import Verdict
from adrcheck.usecases.check import check
from adrcheck.usecases.evaluate import score

EXIT_OK, EXIT_ISSUES, EXIT_CONFLICT, EXIT_UNEVALUATED = 0, 1, 2, 3


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adrcheck", description="Check code changes against architecture decision records, both directions."
    )
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument(
            "--adr-dir",
            default=None,
            help="directory of numbered ADR markdown files (default: the first of docs/adr, docs/decisions, "
            "docs/architecture/decisions, doc/adr, adr, decisions that exists)",
        )
        sp.add_argument("--repo", default=".", help="git repository root (default .)")
        sp.add_argument("--map", default=".adrcheck/map.toml", help="repo-side scope map, relative to --repo")
        sp.add_argument(
            "--compile-model",
            default=None,
            help="provider:model for the compile seat only (default: --model); obligations are cached, so a local "
            "model here costs nothing at judge time",
        )
        sp.add_argument(
            "--model",
            default=None,
            help="provider:model for compiler and judge, e.g. anthropic:claude-sonnet-5-5 or claude-cli:sonnet "
            "(default: anthropic:claude-sonnet-5-5 when the Anthropic key variable is set, else claude-cli:sonnet)",
        )

    c = sub.add_parser("check", help="judge commits against the accepted ADRs")
    common(c)
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--range", help="git revision range, e.g. HEAD~20..HEAD")
    g.add_argument("--commit", help="one commit")
    g.add_argument("--staged", action="store_true", help="the index, as a pre-commit hook sees it")
    c.add_argument("--format", choices=("json", "md"), default="md")
    c.add_argument("--fail-on", choices=("conflict",), help="exit 2 when any CONFLICT is reported")
    c.add_argument(
        "--baseline",
        default=".adrcheck/baseline.json",
        help="reviewed stale rows, relative to --repo; rows named here are counted, not listed (default %(default)s)",
    )
    c.add_argument(
        "--write-baseline",
        action="store_true",
        help="record this run's stale list to --baseline; a deliberate act, review the diff like source",
    )

    k = sub.add_parser("compile", help="compile ADRs into obligations and print them")
    common(k)
    k.add_argument("--prune", action="store_true", help="delete cache entries no current ADR produces")

    e = sub.add_parser("eval", help="score a saved check report (--format json) against frozen cases; no model")
    e.add_argument("--cases", required=True, help="evals/cases/<corpus>.json")
    e.add_argument("--report", required=True, help="output of adrcheck check --format json; written when --run")
    e.add_argument("--run", action="store_true", help="run check over the corpus commits first and write --report")
    e.add_argument("--model", default=None, help="provider:model for --run (default as for check)")
    e.add_argument("--compile-model", default=None, help="provider:model for the compile seat during --run")

    lint_p = sub.add_parser(
        "lint", help="hygiene of the ADR set: dangling refs, cycles, status mismatch, missing status"
    )
    lint_p.add_argument("--adr-dir", default=None)
    lint_p.add_argument("--repo", default=".")
    lint_p.add_argument("--map", default=".adrcheck/map.toml")
    return p


def _default_model() -> str:
    return "anthropic:claude-sonnet-5-5" if os.environ.get("ANTHROPIC_API_KEY") else "claude-cli:sonnet"


def _seats(model: str, compile_model: str | None) -> tuple[ChatModelSeats, ChatModelSeats]:
    """(compiler, judge). One object when the seats share a model, so usage is counted once."""
    judge = ChatModelSeats(runner_for(model))
    if not compile_model or compile_model == model:
        return judge, judge
    return ChatModelSeats(runner_for(compile_model)), judge


def _run_corpus(cases_path: Path, judge, model: str, compile_model: str | None):
    """Execute `check` over a corpus file's commits with the ADRs it was labelled against. The corpus header
    names the repo (`repo`, or `repo_env` for a private one), the ADRs (`adr_dir`, or `adrs_at` for a frozen
    revision) and the commits (`commits`, else every commit the cases name). The repo itself never travels."""
    head = json.loads(cases_path.read_text())
    if "repo_env" in head:
        location = os.environ.get(head["repo_env"])
        if not location:
            raise RuntimeError(f"set {head['repo_env']} to the path of the {head.get('corpus', '')} repository")
        repo = Path(location)
    else:
        repo = Path(head.get("repo", "."))  # as for `check --repo`: relative to the working directory
    git = GitChanges(repo)
    adr_dir = head.get("adr_dir", "docs/adr")
    adrs = adrs_at(git, head["adrs_at"], adr_dir) if "adrs_at" in head else MarkdownAdrSource(repo / adr_dir).adrs()
    adrs, _ = scope(adrs, load_scope_map(repo / ".adrcheck" / "map.toml"))
    commits = head.get("commits") or list(dict.fromkeys(str(c["commit"]) for c in head["cases"]))
    if judge is None:
        compile_seat, judge = _seats(model, compile_model)
    else:
        compile_seat = judge
    compiler = CachedCompiler(compile_seat, repo / ".adrcheck", prompt_version=PROMPT_VERSION)
    changes = [git.changes(f"{c}~1..{c}")[0] for c in commits]
    return check(changes=changes, adrs=adrs, compiler=compiler, judge=judge, repo=git)


def main(argv: list[str] | None = None, judge=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "eval":
        cases = load_cases(Path(args.cases))
        if args.run:
            try:
                reports = _run_corpus(Path(args.cases), judge, args.model or _default_model(), args.compile_model)
            except Exception as exc:
                print(f"could not run the corpus: {type(exc).__name__}: {exc}", file=sys.stderr)
                return EXIT_UNEVALUATED
            Path(args.report).write_text(to_json(reports) + "\n")
            print(f"report written: {args.report}", file=sys.stderr)
        report = json.loads(Path(args.report).read_text())
        result = score(cases, report.get("findings", []))
        for r in result.rows:
            head = f"{r.outcome:6} ADR-{r.case.adr} {r.case.commit} expected {r.case.expected} got {r.got or '-'}"
            print(f"{head}  {r.case.note}".rstrip())
        print(f"{result.hits}/{result.total} hits", file=sys.stderr)
        for (exp, got), n in sorted(result.matrix.items(), key=lambda kv: str(kv[0])):
            print(f"  expected {exp} got {got or 'absent'}: {n}", file=sys.stderr)
        return EXIT_OK if result.hits == result.total else EXIT_ISSUES

    adr_dir = Path(args.adr_dir) if args.adr_dir else discover_adr_dir(Path(args.repo))
    if adr_dir is None:
        print("no ADR directory found; pass --adr-dir", file=sys.stderr)
        return EXIT_ISSUES

    adrs, scope_issues = scope(MarkdownAdrSource(adr_dir).adrs(), load_scope_map(Path(args.repo) / args.map))
    if args.command == "lint":
        issues = lint(adrs) + scope_issues
        for i in issues:
            print(f"{i.kind}\tADR-{i.adr_number}\t{i.detail}")
        if not issues:
            print("ADR set is clean")
        return EXIT_ISSUES if issues else EXIT_OK

    repo = Path(args.repo)
    if judge is None:
        compile_seat, judge = _seats(args.model or _default_model(), args.compile_model)
    else:
        compile_seat = judge  # a test's fake fills both seats
    compiler = CachedCompiler(compile_seat, repo / ".adrcheck", prompt_version=PROMPT_VERSION)
    for i in scope_issues:
        print(f"{i.kind}: ADR-{i.adr_number}: {i.detail}", file=sys.stderr)

    if args.command == "compile":
        spent = 0.0
        for adr in adrs:
            print(f"ADR-{adr.number}: {adr.title} [{adr.status.value}]")
            try:
                obligations = compiler.compile(adr)
            except Exception as exc:
                print(f"could not compile ADR-{adr.number}: {type(exc).__name__}: {exc}", file=sys.stderr)
                return EXIT_UNEVALUATED
            for o in obligations:
                print(f"  {o.id} [{o.kind}, {o.checkability.value}] {o.text}")
                print(f"      quote: {o.quote!r}")
                if o.mandates or o.forbids:
                    print(f"      mandates={list(o.mandates)} forbids={list(o.forbids)}")
            spent += float(getattr(compile_seat, "last_usage", {}).get("cost_usd", 0.0))
            if hasattr(compile_seat, "last_usage"):
                compile_seat.last_usage = {}
        print(f"model cost this run: ${spent:.4f} (cached ADRs cost nothing)", file=sys.stderr)
        if args.prune:
            gone = compiler.prune(adrs)
            print(f"pruned {len(gone)} stale cache entries", file=sys.stderr)
        return EXIT_OK

    git = GitChanges(repo)
    if args.staged:
        changes = [git.staged()]
        if not changes[0].files:
            print("nothing staged", file=sys.stderr)
            return EXIT_OK
    else:
        changes = git.changes(args.range or f"{args.commit}~1..{args.commit}")
    baseline_path = repo / args.baseline
    try:
        reports = check(
            changes=changes, adrs=adrs, compiler=compiler, judge=judge, repo=git, baseline=load_baseline(baseline_path)
        )
    except Exception as exc:
        print(f"could not evaluate: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_UNEVALUATED
    print(to_json(reports) if args.format == "json" else to_markdown(reports))
    if args.write_baseline:
        stale = [s for r in reports for s in r.stale]
        write_baseline(baseline_path, stale)
        print(f"baseline written: {len(stale)} stale obligations -> {baseline_path}", file=sys.stderr)
    conflicts = any(f.verdict is Verdict.CONFLICT for r in reports for f in r.findings)
    if args.fail_on == "conflict" and conflicts:
        return EXIT_CONFLICT
    judged = [r for r in reports if r.judge_calls]
    if judged and all(r.judge_failed for r in judged):
        # ADR-3: abstention never fails the build; this is not abstention. No case got a verdict, so the
        # run says so with its own code instead of a green that nobody earned.
        print("could not evaluate: every judge call failed; see the judge error notes", file=sys.stderr)
        return EXIT_UNEVALUATED
    return EXIT_OK
