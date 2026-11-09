"""Obligations cached on disk, keyed by ADR text and prompt version. Compile once per ADR."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from adrcheck.domain.adr import Adr
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.ports import NotCompiled, ObligationCompiler


class CachedCompiler:
    def __init__(self, inner: ObligationCompiler, directory: Path, prompt_version: str):
        self.inner, self.directory, self.prompt_version = inner, Path(directory), prompt_version

    def _key(self, adr: Adr) -> Path:
        material = json.dumps(
            {"v": self.prompt_version, "title": adr.title, "sections": dict(adr.sections)}, sort_keys=True
        )
        return self.directory / "obligations" / (hashlib.sha256(material.encode()).hexdigest() + ".json")

    def prune(self, adrs: list[Adr]) -> list[Path]:
        """Delete every entry no current ADR text under this prompt version produces. Returns what went."""
        keep = {self._key(a) for a in adrs}
        gone = sorted(p for p in (self.directory / "obligations").glob("*.json") if p not in keep)
        for p in gone:
            p.unlink()
        return gone

    def cached_only(self) -> ObligationCompiler:
        """A view that reads the cache and never calls the model: the free tier's compiler."""
        outer = self

        class CachedOnly:
            def compile(self, adr: Adr) -> tuple[Obligation, ...]:
                if not outer._key(adr).exists():
                    raise NotCompiled(adr)
                return outer.compile(adr)

        return CachedOnly()

    def compile(self, adr: Adr) -> tuple[Obligation, ...]:
        path = self._key(adr)
        if path.exists():
            rows = json.loads(path.read_text())
            return tuple(
                Obligation(
                    **{
                        **r,
                        "checkability": Checkability(r["checkability"]),
                        "mandates": tuple(r.get("mandates", ())),
                        "forbids": tuple(r.get("forbids", ())),
                    }
                )
                for r in rows
            )
        obligations = self.inner.compile(adr)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [{**asdict(o), "checkability": o.checkability.value} for o in obligations]
        path.write_text(json.dumps(rows, indent=1) + "\n")  # committed text; the end-of-file gate wants one newline
        return obligations
