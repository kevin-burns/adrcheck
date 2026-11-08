"""The check use case, with fakes at every port."""

from dataclasses import dataclass, field

from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.verdict import Verdict
from adrcheck.ports import JudgeResponse, RawFinding
from adrcheck.usecases.check import check

ADR = Adr(
    title="One canonical key",
    status=Status.ACCEPTED,
    source="docs/adr/0002-one-key.md",
    number=2,
    applies_to=("enrich/**",),
    sections={
        "context": "Rows used to be keyed by URL, which changed between sweeps.",
        "decision": "Every row is keyed by store.row_key and nothing else.",
        "consequences": "Callers never build a key by hand.",
    },
)
OBLIGATION = Obligation(
    id="ADR-2/1",
    adr_number=2,
    kind="MUST",
    text="Rows are keyed by store.row_key",
    quote="keyed by store.row_key and nothing else",
    checkability=Checkability.STRUCTURAL,
    mandates=("row_key",),
    forbids=('row["url"]',),
)


def change(message="store: key by url again", paths=("enrich/store.py",)):
    files = tuple(
        FileChange(
            path=p,
            old_path=p,
            added=(Line(path=p, kind="+", number=11, text='    key = row["url"]'),),
            removed=(Line(path=p, kind="-", number=11, text="    key = row_key(row)"),),
        )
        for p in paths
    )
    return Change(ref="c1", parent="c0", message=message, files=files)


@dataclass
class FakeCompiler:
    obligations: dict[int, tuple[Obligation, ...]]
    calls: int = 0

    def compile(self, adr):
        self.calls += 1
        return self.obligations.get(adr.number, ())


@dataclass
class FakeJudge:
    response: JudgeResponse
    calls: list = field(default_factory=list)

    def judge(self, change, cases, context):
        self.calls.append((change.ref, tuple(c.adr.number for c in cases)))
        return self.response


@dataclass
class FakeRepo:
    present: dict[tuple[str, str], bool]
    counts: dict[tuple[str, str], int] = field(default_factory=dict)

    def contains(self, ref, needle):
        return self.present.get((ref, needle))

    def occurrences(self, ref, needle):
        return self.counts.get((ref, needle))

    def read(self, ref, path):
        return ""


def raw(verdict=Verdict.CONFLICT, quote=OBLIGATION.quote, line='    key = row["url"]'):
    return RawFinding(
        obligation_id="ADR-2/1",
        verdict=verdict,
        path="enrich/store.py",
        line_text=line,
        quote=quote,
        reason="keys the row by url",
    )


def run(judge_response, present=None, message=None, adrs=None):
    repo = FakeRepo(present if present is not None else {("c0", "row_key"): True, ("c0", 'key = row["url"]'): False})
    judge = FakeJudge(judge_response)
    reports = check(
        changes=[change(message=message) if message else change()],
        adrs=adrs or [ADR],
        compiler=FakeCompiler({2: (OBLIGATION,)}),
        judge=judge,
        repo=repo,
    )
    return reports[0], judge


def test_a_verified_conflict_the_commit_introduced_is_reported_as_conflict():
    report, _ = run(JudgeResponse(findings=(raw(),)))
    [f] = report.findings
    assert (f.adr_number, f.verdict, f.line_text, f.signals) == (
        2,
        Verdict.CONFLICT,
        '    key = row["url"]',
        frozenset({"glob"}),
    )
    assert f.verify_failed == ()


def test_a_claim_that_fails_verification_becomes_unclear_and_says_why():
    report, _ = run(JudgeResponse(findings=(raw(quote="keyed by URL, which changed between sweeps"),)))
    [f] = report.findings
    assert f.verdict is Verdict.UNCLEAR
    assert f.verify_failed == ("quote-outside-decision",)


def test_a_contradiction_already_present_at_the_parent_is_adr_overtaken():
    report, _ = run(
        JudgeResponse(findings=(raw(),)),
        present={("c0", "row_key"): False, ("c0", 'key = row["url"]'): False},
    )
    assert report.findings[0].verdict is Verdict.ADR_OVERTAKEN


def test_the_same_line_already_elsewhere_at_the_parent_is_a_precedent_so_adr_overtaken():
    report, _ = run(
        JudgeResponse(findings=(raw(),)),
        present={("c0", "row_key"): True, ("c0", 'key = row["url"]'): True},
    )
    assert report.findings[0].verdict is Verdict.ADR_OVERTAKEN
    assert "already present at parent" in report.findings[0].note


def test_all_named_anchors_must_be_present_for_the_adr_to_count_as_still_in_force():
    two = Obligation(
        id="ADR-2/1",
        adr_number=2,
        kind="MUST",
        text="t",
        quote=OBLIGATION.quote,
        checkability=Checkability.MECHANICAL,
        mandates=("import_rows", "get"),
    )
    repo = FakeRepo({("c0", "import_rows"): False, ("c0", "get"): True, ("c0", 'key = row["url"]'): False})
    reports = check(
        changes=[change()],
        adrs=[ADR],
        compiler=FakeCompiler({2: (two,)}),
        judge=FakeJudge(JudgeResponse(findings=(raw(),))),
        repo=repo,
    )
    assert reports[0].findings[0].verdict is Verdict.ADR_OVERTAKEN


def test_a_waived_adr_is_not_judged_and_is_reported_compliant_with_the_reason():
    report, judge = run(
        JudgeResponse(findings=(raw(),)),
        message="x\n\nAdr-Exception: ADR-0002 backfill, no row_key here\n",
    )
    assert judge.calls == []
    [f] = report.findings
    assert (f.verdict, f.note) == (Verdict.COMPLIANT, "waived: backfill, no row_key here")


def test_an_unscoped_adr_the_model_calls_irrelevant_is_excluded_with_that_reason():
    unscoped = Adr(title="Unrelated", status=Status.ACCEPTED, source="0009.md", number=9, sections={"decision": "x"})
    report, judge = run(JudgeResponse(not_relevant=frozenset({9})), adrs=[unscoped])
    assert judge.calls == [("c1", (9,))]
    assert [(e.adr_number, e.reason) for e in report.excluded] == [(9, "model: not relevant to this change")]


def test_a_compliant_adr_with_no_findings_is_still_recorded():
    report, _ = run(JudgeResponse(findings=()))
    assert [(f.adr_number, f.verdict) for f in report.findings] == [(2, Verdict.COMPLIANT)]


def test_uncovered_counts_changed_files_no_selected_adr_applies_to():
    repo = FakeRepo({})
    reports = check(
        changes=[
            Change(
                ref="c1",
                parent="c0",
                message="m",
                files=(FileChange("bin/run.sh", "bin/run.sh"), FileChange("enrich/x.py", "enrich/x.py")),
            )
        ],
        adrs=[ADR],
        compiler=FakeCompiler({2: (OBLIGATION,)}),
        judge=FakeJudge(JudgeResponse(findings=())),
        repo=repo,
    )
    assert reports[0].uncovered == 1


def test_a_judge_error_is_an_unclear_finding_that_names_the_error():
    report, _ = run(JudgeResponse(findings=(), error="unparseable judge reply: 'nope'"))
    [f] = report.findings
    assert (f.verdict, f.note) == (Verdict.UNCLEAR, "judge error: unparseable judge reply: 'nope'")


def test_decision_signals_are_attached_to_the_change_report():
    repo = FakeRepo({("c0", "requests"): False, ("c0", "row_key"): True, ("c0", 'row["url"]'): False})
    ch = Change(
        ref="c1",
        parent="c0",
        message="m",
        files=(FileChange("enrich/x.py", "enrich/x.py", added=(Line("enrich/x.py", "+", 1, "import requests"),)),),
    )
    reports = check(
        changes=[ch],
        adrs=[ADR],
        compiler=FakeCompiler({2: (OBLIGATION,)}),
        judge=FakeJudge(JudgeResponse(findings=())),
        repo=repo,
    )
    assert [(s.kind, s.detail) for s in reports[0].decision_signals] == [("new-dependency", "requests")]


def test_a_removed_line_is_never_a_precedent_so_the_conflict_stands():
    # the removed line exists at the parent by definition; that is not "already violated"
    repo = FakeRepo({("c0", "row_key"): True, ("c0", "key = row_key(row)"): True})
    reports = check(
        changes=[change()],
        adrs=[ADR],
        compiler=FakeCompiler({2: (OBLIGATION,)}),
        judge=FakeJudge(JudgeResponse(findings=(raw(line="    key = row_key(row)"),))),
        repo=repo,
    )
    assert reports[0].findings[0].verdict is Verdict.CONFLICT


def test_the_stale_sweep_reports_an_accepted_adr_whose_named_anchors_are_all_gone_at_the_range_end():
    gone = Obligation(
        id="ADR-4/2",
        adr_number=4,
        kind="MUST",
        text="t",
        quote="q",
        checkability=Checkability.MECHANICAL,
        mandates=("import_rows", "li-assist"),
    )
    stale_adr = Adr(
        title="Importer",
        status=Status.ACCEPTED,
        source="0004.md",
        number=4,
        applies_to=("enrich/linkedin.py",),
        sections={"decision": "q"},
    )
    repo = FakeRepo({("c1", "import_rows"): False, ("c1", "li-assist"): False, ("c1", "row_key"): True})
    reports = check(
        changes=[change()],
        adrs=[ADR, stale_adr],
        compiler=FakeCompiler({2: (OBLIGATION,), 4: (gone,)}),
        judge=FakeJudge(JudgeResponse(findings=())),
        repo=repo,
    )
    assert [(s.adr_number, s.obligation_id, s.missing) for s in reports[-1].stale] == [
        (4, "ADR-4/2", ("import_rows", "li-assist"))
    ]


def test_the_stale_sweep_is_quiet_when_anchors_are_present():
    repo = FakeRepo({("c1", "row_key"): True})
    reports = check(
        changes=[change()],
        adrs=[ADR],
        compiler=FakeCompiler({2: (OBLIGATION,)}),
        judge=FakeJudge(JudgeResponse(findings=())),
        repo=repo,
    )
    assert reports[-1].stale == ()


def test_every_selected_adr_goes_to_the_judge_in_one_call_and_findings_come_back_by_obligation_id():
    """One diff, one call: the diff is the cost, so it is sent once however many ADRs apply."""
    other = Adr(
        title="No url keys",
        status=Status.ACCEPTED,
        source="0009.md",
        number=9,
        applies_to=("enrich/**",),
        sections={"decision": "Never key by url."},
    )
    nine = Obligation(
        id="ADR-9/1",
        adr_number=9,
        kind="MUST_NOT",
        text="t",
        quote="Never key by url.",
        checkability=Checkability.INTENT,
    )
    repo = FakeRepo({("c0", "row_key"): True, ("c0", 'key = row["url"]'): False})
    judge = FakeJudge(JudgeResponse(findings=(raw(),), not_relevant=frozenset({9})))
    reports = check(
        changes=[change()],
        adrs=[ADR, other],
        compiler=FakeCompiler({2: (OBLIGATION,), 9: (nine,)}),
        judge=judge,
        repo=repo,
    )
    assert judge.calls == [("c1", (2, 9))]
    assert [(f.adr_number, f.verdict) for f in reports[0].findings] == [(2, Verdict.CONFLICT)]
    assert [(e.adr_number, e.reason) for e in reports[0].excluded] == [(9, "model: not relevant to this change")]


def test_a_finding_for_an_obligation_nobody_asked_about_is_a_problem_not_a_verdict():
    stray = RawFinding("ADR-7/3", Verdict.CONFLICT, "enrich/store.py", 'key = row["url"]', "q", "r")
    report, _ = run(JudgeResponse(findings=(stray,)))
    assert [(f.adr_number, f.verdict) for f in report.findings] == [(2, Verdict.COMPLIANT)]
    assert report.problems == ("judge named ADR-7/3, which was not asked about",)


def test_a_report_records_that_its_judge_call_failed_so_the_caller_can_tell_abstention_from_absence():
    report, _ = run(JudgeResponse(error="AuthenticationError: no credentials"))
    assert report.judge_failed is True and report.judge_calls == 1
    report, _ = run(JudgeResponse(findings=()))
    assert report.judge_failed is False


def test_two_adrs_sharing_a_number_do_not_duplicate_each_others_findings():
    """Seen on a public corpus with two 0007 files: every ADR-7 finding was printed twice."""
    twin = Adr(
        title="Other seven",
        status=Status.ACCEPTED,
        source="0007-b.md",
        number=7,
        applies_to=("enrich/**",),
        sections={"decision": "x"},
    )
    first = Adr(
        title="Seven",
        status=Status.ACCEPTED,
        source="0007-a.md",
        number=7,
        applies_to=("enrich/**",),
        sections={"decision": "y"},
    )
    seven = Obligation(id="ADR-7/1", adr_number=7, kind="MUST", text="t", quote="x", checkability=Checkability.INTENT)
    repo = FakeRepo({("c0", 'key = row["url"]'): False})
    raw7 = RawFinding("ADR-7/1", Verdict.COMPLIANT, "enrich/store.py", 'key = row["url"]', "x", "fine")
    reports = check(
        changes=[change()],
        adrs=[first, twin],
        compiler=FakeCompiler({7: (seven,)}),
        judge=FakeJudge(JudgeResponse(findings=(raw7,))),
        repo=repo,
    )
    # one finding for the obligation that was judged, one ADR-level COMPLIANT for the twin that got nothing
    assert sorted(((f.adr_number, f.obligation_id or "", f.verdict) for f in reports[0].findings), key=str) == [
        (7, "", Verdict.COMPLIANT),
        (7, "ADR-7/1", Verdict.COMPLIANT),
    ]


def test_the_stale_sweep_fires_only_when_every_anchor_of_an_obligation_is_gone():
    """ADR-5: 'an obligation whose named anchors are all missing'. One surviving anchor means the decision still has a foothold."""
    half = Obligation(
        id="ADR-4/1",
        adr_number=4,
        kind="MUST",
        text="t",
        quote="q",
        checkability=Checkability.MECHANICAL,
        mandates=("gone", "still_here"),
    )
    all_gone = Obligation(
        id="ADR-4/2",
        adr_number=4,
        kind="MUST",
        text="t",
        quote="q",
        checkability=Checkability.MECHANICAL,
        mandates=("gone", "also_gone"),
    )
    stale_adr = Adr(
        title="S",
        status=Status.ACCEPTED,
        source="0004.md",
        number=4,
        applies_to=("other/**",),
        sections={"decision": "q"},
    )
    repo = FakeRepo(
        {("c1", "gone"): False, ("c1", "also_gone"): False, ("c1", "still_here"): True, ("c1", "row_key"): True}
    )
    reports = check(
        changes=[change()],
        adrs=[ADR, stale_adr],
        compiler=FakeCompiler({2: (OBLIGATION,), 4: (half, all_gone)}),
        judge=FakeJudge(JudgeResponse(findings=())),
        repo=repo,
    )
    assert [(s.obligation_id, s.missing) for s in reports[-1].stale] == [("ADR-4/2", ("gone", "also_gone"))]


def test_stale_rows_named_in_the_baseline_are_reported_as_known_not_dropped():
    from adrcheck.domain.baseline import Baseline

    gone = Obligation("ADR-4/2", 4, "MUST", "t", "q", Checkability.MECHANICAL, mandates=("import_rows",))
    also = Obligation("ADR-4/3", 4, "MUST", "t", "q", Checkability.MECHANICAL, mandates=("li-assist",))
    stale_adr = Adr(title="Importer", status=Status.ACCEPTED, source="0004.md", number=4, sections={"decision": "q"})
    repo = FakeRepo({("c1", "import_rows"): False, ("c1", "li-assist"): False, ("c1", "row_key"): True})
    reports = check(
        changes=[change()],
        adrs=[ADR, stale_adr],
        compiler=FakeCompiler({2: (OBLIGATION,), 4: (gone, also)}),
        judge=FakeJudge(JudgeResponse(findings=())),
        repo=repo,
        baseline=Baseline(stale=frozenset({(4, "ADR-4/2")})),
    )
    # the reviewed row stays in the report, flagged, so a later --write-baseline can carry it forward
    assert [(s.obligation_id, s.known) for s in reports[-1].stale] == [("ADR-4/2", True), ("ADR-4/3", False)]


IMPORTER = Adr(
    title="Importer",
    status=Status.ACCEPTED,
    source="0004.md",
    number=4,
    applies_to=("enrich/**",),
    sections={"decision": "The LinkedIn importer calls import_rows for every sweep."},
)
IMPORT_OBLIGATION = Obligation(
    "ADR-4/1",
    4,
    "MUST",
    "importer calls import_rows",
    "calls import_rows for every sweep",
    Checkability.STRUCTURAL,
    mandates=("import_rows",),
)


def removal(path="enrich/linkedin.py", text="def import_rows(rows):"):
    files = (FileChange(path=path, old_path=path, removed=(Line(path=path, kind="-", number=3, text=text),)),)
    return Change(ref="c1", parent="c0", message="remove the importer", files=files)


def removal_run(counts):
    repo = FakeRepo({("c0", "import_rows"): True}, counts)
    judged = RawFinding(
        "ADR-4/1",
        Verdict.CONFLICT,
        "enrich/linkedin.py",
        "def import_rows(rows):",
        "calls import_rows for every sweep",
        "the importer is deleted",
    )
    reports = check(
        changes=[removal()],
        adrs=[IMPORTER],
        compiler=FakeCompiler({4: (IMPORT_OBLIGATION,)}),
        judge=FakeJudge(JudgeResponse(findings=(judged,))),
        repo=repo,
    )
    [f] = reports[0].findings
    return f


def test_removing_an_anchor_nothing_called_at_parent_is_overtaken_dead_code_not_a_conflict():
    f = removal_run({("c0", "import_rows"): 1})  # the definition was the only occurrence
    assert f.verdict is Verdict.ADR_OVERTAKEN
    assert "removed anchor import_rows had no callers at parent" in f.note


def test_removing_an_anchor_that_had_callers_at_parent_stays_a_conflict():
    assert removal_run({("c0", "import_rows"): 3}).verdict is Verdict.CONFLICT


def test_without_the_occurrence_probe_the_judge_stands():
    assert removal_run({}).verdict is Verdict.CONFLICT
