from pathlib import Path

from adrcheck.adapters.obligation_cache import CachedCompiler
from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.obligation import Checkability, Obligation

ADR = Adr(title="T", status=Status.ACCEPTED, source="0001.md", number=1, sections={"decision": "d"})
OBL = Obligation(
    id="ADR-1/1", adr_number=1, kind="MUST", text="t", quote="d", checkability=Checkability.MECHANICAL, mandates=("x",)
)


class Counting:
    calls = 0

    def compile(self, adr):
        self.calls += 1
        return (OBL,)


def test_second_compile_of_the_same_adr_text_hits_the_cache(tmp_path: Path):
    inner = Counting()
    cached = CachedCompiler(inner, tmp_path / ".adrcheck", prompt_version="v1")
    assert cached.compile(ADR) == (OBL,)
    assert cached.compile(ADR) == (OBL,)
    assert inner.calls == 1


def test_a_new_prompt_version_or_changed_text_misses(tmp_path: Path):
    inner = Counting()
    CachedCompiler(inner, tmp_path / ".adrcheck", prompt_version="v1").compile(ADR)
    CachedCompiler(inner, tmp_path / ".adrcheck", prompt_version="v2").compile(ADR)
    changed = Adr(title="T", status=Status.ACCEPTED, source="0001.md", number=1, sections={"decision": "d2"})
    CachedCompiler(inner, tmp_path / ".adrcheck", prompt_version="v2").compile(changed)
    assert inner.calls == 3


def test_a_cache_entry_is_a_committable_text_file_ending_in_one_newline(tmp_path: Path):
    """The cache is committed (ADR-4); a file without a trailing newline trips the end-of-file gate on every commit."""
    cached = CachedCompiler(Counting(), tmp_path / ".adrcheck", prompt_version="v1")
    cached.compile(ADR)
    [entry] = (tmp_path / ".adrcheck" / "obligations").glob("*.json")
    assert entry.read_text().endswith("]\n")
