"""The baseline file: reviewed stale rows, read and written at the edge."""

import json
from pathlib import Path

from adrcheck.adapters.baseline_file import load_baseline, write_baseline
from adrcheck.domain.baseline import Baseline
from adrcheck.usecases.check import StaleAdr


def test_a_missing_file_is_an_empty_baseline(tmp_path: Path):
    assert load_baseline(tmp_path / "none.json") == Baseline()


def test_written_rows_round_trip_and_the_file_is_reviewable_json(tmp_path: Path):
    path = tmp_path / ".adrcheck" / "baseline.json"
    rows = [StaleAdr(4, "ADR-4/2", ("import_rows", "li-assist")), StaleAdr(7, "ADR-7/1", ("Clef",), known=True)]
    write_baseline(path, rows)
    text = path.read_text()
    assert text.endswith("\n") and json.loads(text)["stale"][0] == {
        "adr": 4,
        "obligation": "ADR-4/2",
        "missing": ["import_rows", "li-assist"],
    }
    loaded = load_baseline(path)
    assert loaded.knows(4, "ADR-4/2") and loaded.knows(7, "ADR-7/1") and not loaded.knows(4, "ADR-4/9")
