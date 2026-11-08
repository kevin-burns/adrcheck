"""Check changes against ADRs: select, compile, judge, verify, classify. No I/O of its own."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change
from adrcheck.domain.decision_signals import DecisionSignal, decision_signals
from adrcheck.domain.exception import parse_exceptions
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.overtaken import classify
from adrcheck.domain.select import Selection, select
from adrcheck.domain.verdict import Verdict
from adrcheck.domain.verify import Claim, verify
from adrcheck.ports import ChangeJudge, Context, JudgeCase, ObligationCompiler, RepoReader

POST_IMAGE_BUDGET_CHARS = 60_000


@dataclass(frozen=True)
class Finding:
    adr_number: int
    obligation_id: str | None
    verdict: Verdict
    signals: frozenset[str]
    path: str = ""
    line_text: str = ""
    quote: str = ""
    reason: str = ""
    verify_failed: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class Excluded:
    adr_number: int | None
    reason: str


@dataclass(frozen=True)
class StaleAdr:
    """An accepted ADR whose named anchors are no longer all present at the end of the range."""

    adr_number: int
    obligation_id: str
    missing: tuple[str, ...]


@dataclass(frozen=True)
class ChangeReport:
    ref: str
    message: str
    findings: tuple[Finding, ...] = ()
    excluded: tuple[Excluded, ...] = ()
    problems: tuple[str, ...] = ()
    uncovered: int = 0
    judge_calls: int = 0
    judge_failed: bool = False  # the judge was called and returned no verdict at all (error, not abstention)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    decision_signals: tuple[DecisionSignal, ...] = ()
    stale: tuple[StaleAdr, ...] = ()  # populated on the last report of a run


def stale_sweep(adrs: list[Adr], compiler: ObligationCompiler, repo: RepoReader, ref: str) -> tuple[StaleAdr, ...]:
    """Per run, not per diff: a stale ADR's files may never be touched again, so selection cannot find it."""
    out: list[StaleAdr] = []
    for adr in adrs:
        if adr.status is not Status.ACCEPTED or adr.number is None:
            continue
        for o in compiler.compile(adr):
            missing = tuple(n for n in o.mandates if repo.contains(ref, n) is False)
            if missing:
                out.append(StaleAdr(adr.number, o.id, missing))
    return tuple(out)


def _all_present(repo: RepoReader, ref: str | None, needles: tuple[str, ...]) -> bool | None:
    """Were all the things the ADR names still in the tree at `ref`? None when nothing to probe."""
    if ref is None or not needles:
        return None
    results = [repo.contains(ref, n) for n in needles]
    if all(r is None for r in results):
        return None
    return all(r is True for r in results)


def _precedent(repo: RepoReader, change: Change, path: str, line_text: str) -> bool | None:
    """Did the very line the judge cites already exist somewhere at the parent? Then this commit set no precedent.

    Only an ADDED line can be a precedent question; a removed line existed at the parent by definition.
    """
    text = line_text.strip()
    if (
        text[:1] in "+-"
        and not change.touched(path, text, kinds=("+",))
        and change.touched(path, text[1:], kinds=("+",))
    ):
        text = text[1:].strip()
    if change.parent is None or len(text) < 8 or not change.touched(path, text, kinds=("+",)):
        return None
    return repo.contains(change.parent, text)


def _post_image(repo: RepoReader, ref: str, path: str) -> str | None:
    """The file after the change, or None when it no longer exists (a deleted file has no post-image)."""
    try:
        return repo.read(ref, path)
    except Exception:
        return None


def _context(repo: RepoReader, change: Change) -> Context:
    images: dict[str, str] = {}
    spent = 0
    for f in change.files:
        if spent >= POST_IMAGE_BUDGET_CHARS:
            break
        text = _post_image(repo, change.ref, f.path)
        if text is None:
            continue
        images[f.path] = text[: POST_IMAGE_BUDGET_CHARS - spent]
        spent += len(images[f.path])
    return Context(post_images=images)


def _uncovered(change: Change, selected: list[Selection]) -> int:
    from adrcheck.domain.select import _glob_matches

    globs = [g for s in selected for g in s.adr.applies_to]
    return sum(1 for p in change.paths() if not any(_glob_matches(g, p) for g in globs))


def check(
    *,
    changes: list[Change],
    adrs: list[Adr],
    compiler: ObligationCompiler,
    judge: ChangeJudge,
    repo: RepoReader,
) -> list[ChangeReport]:
    reports: list[ChangeReport] = []
    for change in changes:
        waived, problems = parse_exceptions(change.message)
        waived_by_number = {w.adr_number: w.reason for w in waived}
        known = {a.number for a in adrs}
        problems += tuple(
            f"Adr-Exception names ADR-{w.adr_number}, which does not exist" for w in waived if w.adr_number not in known
        )

        selection = select(adrs, change)
        findings: list[Finding] = []
        excluded = [Excluded(e.adr.number, e.reason) for e in selection.excluded]
        calls = tokens_in = tokens_out = 0
        cost = 0.0
        judge_failed = False
        context: Context | None = None
        judged: list[Selection] = []

        cases: list[tuple[Selection, JudgeCase]] = []
        for sel in list(selection.selected) + list(selection.undetermined):
            adr = sel.adr
            if adr.number in waived_by_number:
                findings.append(
                    Finding(
                        adr.number, None, Verdict.COMPLIANT, sel.signals, note=f"waived: {waived_by_number[adr.number]}"
                    )
                )
                judged.append(sel)
                continue
            obligations = compiler.compile(adr)
            checkable = tuple(o for o in obligations if o.checkability is not Checkability.PROCESS)
            cases.append((Selection(adr, sel.signals or frozenset({"model"})), JudgeCase(adr, checkable)))

        if cases:
            context = _context(repo, change)
            response = judge.judge(change, tuple(case for _, case in cases), context)
            calls += 1
            judge_failed = bool(response.error)
            tokens_in += response.tokens_in
            tokens_out += response.tokens_out
            cost += response.cost_usd
            by_id = {o.id: (sel, case) for sel, case in cases for o in case.obligations}
            by_number = {case.adr.number: (sel, case) for sel, case in cases}
            findings_of: dict[int | None, list[Finding]] = {case.adr.number: [] for _, case in cases}
            for raw in response.findings:
                owner = by_id.get(raw.obligation_id) or by_number.get(_adr_number_of(raw.obligation_id))
                if owner is None:
                    problems += (f"judge named {raw.obligation_id}, which was not asked about",)
                    continue
                sel, case = owner
                obligation = next((o for o in case.obligations if o.id == raw.obligation_id), None)
                findings_of[case.adr.number].append(_settle(raw, obligation, change, case.adr, sel.signals, repo))
            for sel, case in cases:
                adr = case.adr
                if response.error:
                    judged.append(sel)
                    findings.append(
                        Finding(adr.number, None, Verdict.UNCLEAR, sel.signals, note=f"judge error: {response.error}")
                    )
                elif adr.number in response.not_relevant:
                    excluded.append(Excluded(adr.number, "model: not relevant to this change"))
                else:
                    judged.append(sel)
                    compliant = Finding(adr.number, None, Verdict.COMPLIANT, sel.signals)
                    findings.extend(findings_of[adr.number] or [compliant])

        reports.append(
            ChangeReport(
                ref=change.ref,
                message=change.message,
                findings=tuple(findings),
                excluded=tuple(excluded),
                problems=problems,
                uncovered=_uncovered(change, judged),
                judge_calls=calls,
                judge_failed=judge_failed,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                decision_signals=decision_signals(
                    change, lambda needle, parent=change.parent: repo.contains(parent, needle) if parent else None
                ),
            )
        )
    if reports:
        last = reports[-1]
        reports[-1] = replace(last, stale=stale_sweep(adrs, compiler, repo, last.ref))
    return reports


_OBLIGATION_ID = re.compile(r"ADR-(\d+)/")


def _adr_number_of(obligation_id: str) -> int | None:
    m = _OBLIGATION_ID.match(obligation_id)
    return int(m.group(1)) if m else None


def _settle(
    raw, obligation: Obligation | None, change: Change, adr: Adr, signals: frozenset[str], repo: RepoReader
) -> Finding:
    verdict = raw.verdict
    failed: tuple[str, ...] = ()
    note = ""
    if obligation is None:
        failed = ("unknown-obligation",)
    if verdict is Verdict.CONFLICT or (obligation and failed == ()):
        result = verify(
            Claim(adr_number=adr.number or 0, path=raw.path, line_text=raw.line_text, quote=raw.quote), change, adr
        )
        failed = failed + result.failed
    if failed and verdict is Verdict.CONFLICT:
        verdict = Verdict.UNCLEAR
        note = "claim failed verification: " + ", ".join(failed)
    mandated = _all_present(repo, change.parent, obligation.mandates) if obligation else None
    forbidden = _precedent(repo, change, raw.path, raw.line_text) if verdict is Verdict.CONFLICT else None
    settled = classify(verdict, mandated_at_parent=mandated, forbidden_at_parent=forbidden)
    if settled is Verdict.ADR_OVERTAKEN and settled is not verdict:
        note = (note + "; " if note else "") + "contradiction already present at parent commit"
    return Finding(
        adr_number=adr.number or 0,
        obligation_id=raw.obligation_id,
        verdict=settled,
        signals=signals,
        path=raw.path,
        line_text=raw.line_text,
        quote=raw.quote,
        reason=raw.reason,
        verify_failed=failed,
        note=note,
    )
