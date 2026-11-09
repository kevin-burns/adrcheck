"""The free tier's judge: no model. An obligation's forbidden patterns found on an added line are a CONFLICT
claim with the obligation's own quote, which then goes through the same verify() as a model's claim."""

from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.mechanical import MechanicalJudge
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.verdict import Verdict
from adrcheck.ports import Context, JudgeCase

ADR = Adr(title="Billing through the API", status=Status.ACCEPTED, source="0001.md", number=1, sections={})
FORBIDS = Obligation(
    "ADR-1/2",
    1,
    "MUST_NOT",
    "billing never imports ledger.db",
    "It never imports `ledger.db`.",
    Checkability.MECHANICAL,
    forbids=("import ledger.db", "from ledger.db"),
)
MANDATES = Obligation(
    "ADR-1/1", 1, "MUST", "billing uses Ledger", "only through `Ledger`", Checkability.STRUCTURAL, mandates=("Ledger",)
)


def change(added=(), removed=(), path="services/billing/invoices.py"):
    f = FileChange(
        path=path,
        old_path=path,
        added=tuple(Line(path=path, kind="+", number=i + 1, text=t) for i, t in enumerate(added)),
        removed=tuple(Line(path=path, kind="-", number=i + 1, text=t) for i, t in enumerate(removed)),
    )
    return Change(ref="c1", parent="c0", message="m", files=(f,))


def test_a_forbidden_pattern_on_an_added_line_is_a_conflict_claim_with_the_obligations_quote():
    ch = change(added=("from ledger.db import connection", "x = 1"))
    resp = MechanicalJudge().judge(ch, (JudgeCase(ADR, (FORBIDS, MANDATES)),), Context(post_images={}))
    [f] = resp.findings
    assert (f.obligation_id, f.verdict, f.path, f.line_text) == (
        "ADR-1/2",
        Verdict.CONFLICT,
        ch.files[0].path,
        "from ledger.db import connection",
    )
    assert f.quote == FORBIDS.quote and "from ledger.db" in f.reason
    assert resp.cost_usd == 0.0 and resp.tokens_in == 0


def test_a_removed_line_and_an_obligation_with_only_mandates_produce_nothing():
    ch = change(removed=("from ledger.db import connection",), added=("from ledger.api import Ledger",))
    resp = MechanicalJudge().judge(ch, (JudgeCase(ADR, (FORBIDS, MANDATES)),), Context(post_images={}))
    assert resp.findings == () and resp.not_relevant == frozenset()


def test_one_claim_per_obligation_and_line_even_when_two_patterns_match():
    ch = change(added=("import ledger.db; from ledger.db import x",))
    resp = MechanicalJudge().judge(ch, (JudgeCase(ADR, (FORBIDS,)),), Context(post_images={}))
    assert len(resp.findings) == 1
