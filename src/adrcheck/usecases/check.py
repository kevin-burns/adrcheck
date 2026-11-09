"""Check changes against ADRs: select, compile, judge, verify, classify. No I/O of its own."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.baseline import EMPTY, Baseline
from adrcheck.domain.change import Change
from adrcheck.domain.decision_signals import DecisionSignal, decision_signals
from adrcheck.domain.exception import parse_exceptions
from adrcheck.domain.mechanical import MechanicalJudge
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.overtaken import classify
from adrcheck.domain.select import Selection, select
from adrcheck.domain.verdict import Verdict
from adrcheck.domain.verify import Claim, verify
from adrcheck.ports import ChangeJudge, Context, JudgeCase, NotCompiled, ObligationCompiler, RepoReader

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
    known: bool = False  # already reviewed: the baseline names this row


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


def stale_sweep(
    adrs: list[Adr], compiler: ObligationCompiler, repo: RepoReader, ref: str, baseline: Baseline = EMPTY
) -> tuple[StaleAdr, ...]:
    """Per run, not per diff: a stale ADR's files may never be touched again, so selection cannot find it."""
    out: list[StaleAdr] = []
    for adr in adrs:
        if adr.status is not Status.ACCEPTED or adr.number is None:
            continue
        try:
            obligations = compiler.compile(adr)
        except NotCompiled:
            continue  # free tier with a cold cache: the change report already says so
        for o in obligations:
            # ADR-5: stale only when every named anchor is gone. One surviving anchor is a foothold.
            missing = tuple(n for n in o.mandates if repo.contains(ref, n) is False)
            if missing and len(missing) == len(o.mandates):
                out.append(StaleAdr(adr.number, o.id, missing, known=baseline.knows(adr.number, o.id)))
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


_IDENTIFIER = re.compile(r"^\w+$")
_DEFINITION = re.compile(r"^\s*(?:(?:async\s+)?def|class)\s+(\w+)|^\s*(\w+)\s*(?::[^=]*)?=[^=]")


def _dead_removal(repo: RepoReader, change: Change, adr_anchors: tuple[str, ...], raw) -> str | None:
    """The name this conflict removed, if nothing but its own definition referenced it at the parent.

    A removal has no added line for `_precedent` to find, and the name did exist at the parent, so the two
    older probes say nothing. One whole-identifier count over the parent's code settles it: a lone occurrence
    is the definition. Candidates are the name the removed line defines and any identifier anchor of the ADR
    (not only of the cited obligation: the judge files a line under one obligation, the anchors sit on another).
    """
    if change.parent is None or not change.touched(raw.path, raw.line_text, kinds=("-",)):
        return None
    if change.touched(raw.path, raw.line_text, kinds=("+",)):
        return None  # moved, not removed
    candidates: list[str] = []
    if m := _DEFINITION.match(raw.line_text):
        candidates.append(m.group(1) or m.group(2))
    candidates += [n for n in adr_anchors if _IDENTIFIER.match(n) and n in raw.line_text and n not in candidates]
    for name in candidates:
        count = repo.occurrences(change.parent, name)
        if count is not None and count <= 1:
            return name
    return None


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
    baseline: Baseline = EMPTY,
    max_calls: int | None = None,
    tier: str = "judge",
) -> list[ChangeReport]:
    """`max_calls` caps judge calls for the run. A change past the budget is not judged: its selected ADRs read
    UNCLEAR with the reason and the report carries a problem line, so a capped run is visibly partial, never a
    green nobody earned.

    `tier="free"` (bead 2wa): no model. Forbidden patterns on added lines are judged by `MechanicalJudge`, an
    ADR with no mechanical hit is excluded as not judged, and an ADR with no cached compile is excluded as not
    compiled with a problem line. Nothing in the free tier can be a COMPLIANT nobody earned."""
    free = tier == "free"
    if free:
        judge = MechanicalJudge()
    reports: list[ChangeReport] = []
    total_calls = 0
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
            try:
                obligations = compiler.compile(adr)
            except NotCompiled:
                problems += (f"ADR-{adr.number} not compiled; run adrcheck compile",)
                excluded.append(Excluded(adr.number, "not compiled"))
                continue
            checkable = tuple(o for o in obligations if o.checkability is not Checkability.PROCESS)
            cases.append((Selection(adr, sel.signals or frozenset({"model"})), JudgeCase(adr, checkable)))

        if cases and max_calls is not None and total_calls >= max_calls:
            n = len(cases)
            problems += (
                f"judge call budget of {max_calls} reached; {n} ADR{'s' if n != 1 else ''} not judged for this change",
            )
            for sel, case in cases:
                judged.append(sel)
                findings.append(
                    Finding(
                        case.adr.number,
                        None,
                        Verdict.UNCLEAR,
                        sel.signals,
                        note=f"not judged: call budget of {max_calls} reached",
                    )
                )
            cases = []

        if cases:
            context = _context(repo, change)
            response = judge.judge(change, tuple(case for _, case in cases), context)
            if not free:
                calls += 1
                total_calls += 1
            judge_failed = bool(response.error)
            tokens_in += response.tokens_in
            tokens_out += response.tokens_out
            cost += response.cost_usd
            # Cases are keyed by position, not ADR number: two records can share a number (lint says so),
            # and a finding must land on exactly one of them.
            by_id = {o.id: i for i, (_, case) in enumerate(cases) for o in case.obligations}
            by_number = {case.adr.number: i for i, (_, case) in enumerate(cases)}
            findings_of: list[list[Finding]] = [[] for _ in cases]
            for raw in response.findings:
                owner = by_id.get(raw.obligation_id)
                if owner is None:
                    owner = by_number.get(_adr_number_of(raw.obligation_id))
                if owner is None:
                    problems += (f"judge named {raw.obligation_id}, which was not asked about",)
                    continue
                sel, case = cases[owner]
                obligation = next((o for o in case.obligations if o.id == raw.obligation_id), None)
                anchors = tuple(n for o in case.obligations for n in o.mandates)
                findings_of[owner].append(_settle(raw, obligation, change, case.adr, sel.signals, repo, anchors))
            findings_of = [_reconcile(group) for group in findings_of]
            for i, (sel, case) in enumerate(cases):
                adr = case.adr
                if response.error:
                    judged.append(sel)
                    findings.append(
                        Finding(adr.number, None, Verdict.UNCLEAR, sel.signals, note=f"judge error: {response.error}")
                    )
                elif adr.number in response.not_relevant:
                    excluded.append(Excluded(adr.number, "model: not relevant to this change"))
                elif free and not findings_of[i]:
                    excluded.append(Excluded(adr.number, "free tier: no mechanical rule fired; judge not run"))
                else:
                    judged.append(sel)
                    compliant = Finding(adr.number, None, Verdict.COMPLIANT, sel.signals)
                    findings.extend(findings_of[i] or [compliant])

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
        reports[-1] = replace(last, stale=stale_sweep(adrs, compiler, repo, last.ref, baseline))
    return reports


_OBLIGATION_ID = re.compile(r"ADR-(\d+)/")


def _reconcile(group: list[Finding]) -> list[Finding]:
    """One ADR, one line, two obligations, opposite verdicts: the judge has contradicted itself and neither
    answer is reported as settled (bead rnr). Both become UNCLEAR with the pair named."""
    by_line: dict[tuple[str, str], list[int]] = {}
    for i, f in enumerate(group):
        if f.line_text:
            by_line.setdefault((f.path, f.line_text), []).append(i)
    for idxs in by_line.values():
        verdicts = {group[i].verdict for i in idxs}
        if Verdict.CONFLICT in verdicts and Verdict.COMPLIANT in verdicts:
            named = ", ".join(f"{group[i].obligation_id} {group[i].verdict.value}" for i in idxs)
            for i in idxs:
                group[i] = replace(
                    group[i], verdict=Verdict.UNCLEAR, note=f"judge contradicts itself on this line: {named}"
                )
    return group


def _adr_number_of(obligation_id: str) -> int | None:
    m = _OBLIGATION_ID.match(obligation_id)
    return int(m.group(1)) if m else None


def _settle(
    raw,
    obligation: Obligation | None,
    change: Change,
    adr: Adr,
    signals: frozenset[str],
    repo: RepoReader,
    adr_anchors: tuple[str, ...] = (),
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
    dead_anchor = _dead_removal(repo, change, adr_anchors, raw) if verdict is not Verdict.COMPLIANT else None
    settled = classify(
        verdict, mandated_at_parent=mandated, forbidden_at_parent=forbidden, dead_at_parent=dead_anchor is not None
    )
    if settled is Verdict.ADR_OVERTAKEN and settled is not verdict:
        why = (
            f"removed anchor {dead_anchor} had no callers at parent"
            if dead_anchor
            else "contradiction already present at parent commit"
        )
        note = (note + "; " if note else "") + why
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
