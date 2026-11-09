"""explain: one ADR's obligations with where each anchor lives at a ref. No model beyond the cached compile."""

from dataclasses import dataclass, field

from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.usecases.explain import explain

ADR = Adr(title="Key", status=Status.ACCEPTED, source="0002-key.md", number=2, applies_to=("enrich/**",), sections={})
OBLIGATION = Obligation(
    "ADR-2/1",
    2,
    "MUST",
    "rows keyed by row_key",
    "keyed by `row_key`",
    Checkability.STRUCTURAL,
    mandates=("row_key", "enrich/store.py"),
    forbids=('row["url"]',),
)


@dataclass
class FakeRepo:
    where: dict[tuple[str, str], list[str] | None]
    counts: dict[tuple[str, str], int] = field(default_factory=dict)

    def contains(self, ref, needle):
        files = self.where.get((ref, needle))
        return None if files is None else bool(files)

    def occurrences(self, ref, needle):
        return self.counts.get((ref, needle))

    def locate(self, ref, needle):
        return self.where.get((ref, needle))

    def read(self, ref, path):
        return ""


class FakeCompiler:
    def compile(self, adr):
        return (OBLIGATION,)


def test_each_anchor_reports_the_files_that_hold_it_and_how_often_it_is_used():
    repo = FakeRepo(
        {
            ("HEAD", "row_key"): ["enrich/keys.py", "enrich/store.py"],
            ("HEAD", "enrich/store.py"): ["enrich/store.py"],
            ("HEAD", 'row["url"]'): [],
        },
        {("HEAD", "row_key"): 4, ("HEAD", "enrich/store.py"): 0},
    )
    [report] = explain(ADR, FakeCompiler(), repo, "HEAD")
    assert report.obligation is OBLIGATION
    by_name = {a.name: a for a in report.anchors}
    assert by_name["row_key"].files == ("enrich/keys.py", "enrich/store.py") and by_name["row_key"].count == 4
    assert by_name["enrich/store.py"].files == ("enrich/store.py",)
    assert by_name['row["url"]'].forbidden and by_name['row["url"]'].files == ()
    assert report.stale is False


def test_an_obligation_whose_every_mandated_anchor_is_gone_is_stale_and_a_forbidden_hit_is_named():
    repo = FakeRepo(
        {("HEAD", "row_key"): [], ("HEAD", "enrich/store.py"): [], ("HEAD", 'row["url"]'): ["enrich/store.py"]},
        {("HEAD", "row_key"): 0},
    )
    [report] = explain(ADR, FakeCompiler(), repo, "HEAD")
    assert report.stale is True
    assert {a.name for a in report.anchors if a.forbidden and a.files} == {'row["url"]'}


def test_an_unreadable_ref_leaves_every_anchor_unknown_rather_than_missing():
    [report] = explain(ADR, FakeCompiler(), FakeRepo({}), "no-such-ref")
    assert all(a.files is None for a in report.anchors) and report.stale is None
