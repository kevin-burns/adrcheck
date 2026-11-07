"""Composition root. Parses flags, wires adapters to use cases, renders. No logic of its own."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adrcheck.adapters.claude_judge import PROMPT_VERSION, ClaudeJudge
from adrcheck.adapters.eval_cases import load_cases
from adrcheck.adapters.git_changes import GitChanges
from adrcheck.adapters.markdown_adr_source import MarkdownAdrSource
from adrcheck.adapters.obligation_cache import CachedCompiler
from adrcheck.adapters.render import to_json, to_markdown
from adrcheck.domain.lint import lint
from adrcheck.domain.verdict import Verdict
from adrcheck.usecases.check import check
from adrcheck.usecases.evaluate import score

EXIT_OK, EXIT_ISSUES, EXIT_CONFLICT = 0, 1, 2


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adrcheck", description="Check code changes against architecture decision records, both directions."
    )
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument(
            "--adr-dir", default="docs/adr", help="directory of numbered ADR markdown files (default docs/adr)"
        )
        sp.add_argument("--repo", default=".", help="git repository root (default .)")
        sp.add_argument("--model", default="sonnet", help="model for the judge via claude -p (default sonnet)")

    c = sub.add_parser("check", help="judge commits against the accepted ADRs")
    common(c)
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--range", help="git revision range, e.g. HEAD~20..HEAD")
    g.add_argument("--commit", help="one commit")
    g.add_argument("--staged", action="store_true", help="(not yet) the staged diff")
    c.add_argument("--format", choices=("json", "md"), default="md")
    c.add_argument("--fail-on", choices=("conflict",), help="exit 2 when any CONFLICT is reported")

    k = sub.add_parser("compile", help="compile ADRs into obligations and print them")
    common(k)
    k.add_argument("--prune", action="store_true", help="delete cache entries no current ADR produces")

    e = sub.add_parser("eval", help="score a saved check report (--format json) against frozen cases; no model")
    e.add_argument("--cases", required=True, help="evals/cases/<corpus>.json")
    e.add_argument("--report", required=True, help="output of adrcheck check --format json")

    lint_p = sub.add_parser(
        "lint", help="hygiene of the ADR set: dangling refs, cycles, status mismatch, missing status"
    )
    lint_p.add_argument("--adr-dir", default="docs/adr")
    return p


def main(argv: list[str] | None = None, judge=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "eval":
        cases = load_cases(Path(args.cases))
        report = json.loads(Path(args.report).read_text())
        result = score(cases, report.get("findings", []))
        for r in result.rows:
            head = f"{r.outcome:6} ADR-{r.case.adr} {r.case.commit} expected {r.case.expected} got {r.got or '-'}"
            print(f"{head}  {r.case.note}".rstrip())
        print(f"{result.hits}/{result.total} hits", file=sys.stderr)
        for (exp, got), n in sorted(result.matrix.items(), key=lambda kv: str(kv[0])):
            print(f"  expected {exp} got {got or 'absent'}: {n}", file=sys.stderr)
        return EXIT_OK if result.hits == result.total else EXIT_ISSUES

    adr_dir = Path(args.adr_dir)

    if args.command == "lint":
        issues = lint(MarkdownAdrSource(adr_dir).adrs())
        for i in issues:
            print(f"{i.kind}\tADR-{i.adr_number}\t{i.detail}")
        if not issues:
            print("ADR set is clean")
        return EXIT_ISSUES if issues else EXIT_OK

    repo = Path(args.repo)
    judge = judge or ClaudeJudge(model=args.model)
    compiler = CachedCompiler(judge, repo / ".adrcheck", prompt_version=PROMPT_VERSION)
    adrs = MarkdownAdrSource(adr_dir).adrs()

    if args.command == "compile":
        spent = 0.0
        for adr in adrs:
            print(f"ADR-{adr.number}: {adr.title} [{adr.status.value}]")
            for o in compiler.compile(adr):
                print(f"  {o.id} [{o.kind}, {o.checkability.value}] {o.text}")
                print(f"      quote: {o.quote!r}")
                if o.mandates or o.forbids:
                    print(f"      mandates={list(o.mandates)} forbids={list(o.forbids)}")
            spent += float(getattr(judge, "last_usage", {}).get("cost_usd", 0.0))
            if hasattr(judge, "last_usage"):
                judge.last_usage = {}
        print(f"model cost this run: ${spent:.4f} (cached ADRs cost nothing)", file=sys.stderr)
        if args.prune:
            gone = compiler.prune(adrs)
            print(f"pruned {len(gone)} stale cache entries", file=sys.stderr)
        return EXIT_OK

    if args.staged:
        print("--staged is not implemented yet; use --commit or --range", file=sys.stderr)
        return EXIT_ISSUES
    git = GitChanges(repo)
    changes = git.changes(args.range or f"{args.commit}~1..{args.commit}")
    reports = check(changes=changes, adrs=adrs, compiler=compiler, judge=judge, repo=git)
    print(to_json(reports) if args.format == "json" else to_markdown(reports))
    conflicts = any(f.verdict is Verdict.CONFLICT for r in reports for f in r.findings)
    return EXIT_CONFLICT if (args.fail_on == "conflict" and conflicts) else EXIT_OK
