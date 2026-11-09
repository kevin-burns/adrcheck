"""Build the planted corpus: a small git repository with five ADRs and nine commits, some of which break a
decision on purpose. Labels are true by construction, so this corpus measures a judge's recall on
CONFLICT and ADR-OVERTAKEN, which a corpus of real compliant commits cannot.

    python evals/planted/build.py /path/to/dest
    export ADRCHECK_EVAL_PLANTED_REPO=/path/to/dest
    adrcheck eval --cases evals/cases/planted.json --run --report /tmp/planted.json

Author, dates and configuration are pinned, so the commit hashes are the same on every machine and the
cases file can name them. Change anything here and the hashes change: rebuild, then update the cases.
Standard library only; no personal data; nothing here is a real project.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - argv-list calls to git only, no shell
import sys
from pathlib import Path

ENV = {
    **{k: v for k, v in os.environ.items() if k in ("PATH", "HOME")},
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Planted Corpus",
    "GIT_AUTHOR_EMAIL": "planted@example.invalid",
    "GIT_COMMITTER_NAME": "Planted Corpus",
    "GIT_COMMITTER_EMAIL": "planted@example.invalid",
}

ADR_1 = """# 1. Billing reads the ledger through its API

Date: 2026-01-10
Status: Accepted
Applies to: services/billing/**

## Context

Two outages came from billing code holding a transaction open on the ledger table while it waited on a
network call. The ledger package owns its locking; callers should not see the table.

## Decision

Code under `services/billing/` reads and writes ledger entries only through `Ledger` in `ledger/api.py`.
It never imports `ledger.db`.

## Consequences

Billing cannot tune a query by hand. Every ledger access is observable in one place.
"""

ADR_2 = """# 2. Services talk to each other through the outbox

Date: 2026-01-18
Status: Accepted
Applies to: services/**/api/**

## Context

Synchronous calls between services turned one slow deploy into a cascade. Events through the outbox table
are delivered after commit, by a worker, with retries.

## Decision

HTTP handlers under `services/*/api/` publish domain events with `publish()` from `events/outbox.py`.
They never import `requests` or call another service's HTTP endpoint from a request handler.

## Consequences

A handler cannot wait for another service's answer. Anything that needs an answer is a query, not an event.
"""

ADR_3 = """# 3. Amounts are Money, not floats

Date: 2026-02-02
Status: Accepted
Applies to: services/billing/**, libs/money/**

## Context

A 0.1 + 0.2 rounding error reached an invoice.

## Decision

Amounts are instances of `Money` from `libs/money/money.py`, which holds minor units as an integer.
No amount is stored or passed as a `float`.

## Consequences

Percentages are applied by `Money.scaled()`, which rounds once, half-even, and is tested.
"""

ADR_4 = """# 4. CSV ingestion has one entry point

Date: 2026-02-20
Status: Accepted
Applies to: ingest/**

## Context

Three scripts parsed the same bank export three different ways.

## Decision

`import_rows()` in `ingest/importer.py` is the only entry point for CSV ingestion. Every CSV read goes
through it.

## Consequences

A format change is one edit. The importer is the place to add validation.
"""

ADR_5 = """# 5. Invoice numbers come from one sequence

Date: 2026-03-01
Status: Proposed
Applies to: services/billing/**

## Context

Numbers are assigned in two places today and have collided once.

## Decision

Invoices are numbered by `next_invoice_number()` in `services/billing/numbering.py` and nowhere else.

## Consequences

Numbering becomes a single point of contention; acceptable at our volume.
"""

LEDGER_API = '''"""The ledger's public face. Billing and everything else goes through here (ADR-1)."""

from ledger import db


class Ledger:
    def __init__(self, conn=None):
        self._conn = conn or db.connection()

    def balance(self, account: str) -> int:
        return db.sum_minor_units(self._conn, account)

    def post(self, account: str, minor_units: int, memo: str) -> None:
        db.insert_entry(self._conn, account, minor_units, memo)
'''

LEDGER_DB = '''"""Table access for the ledger. Private to the ledger package."""

import sqlite3


def connection():
    conn = sqlite3.connect(":memory:")
    conn.execute("create table if not exists entries(account text, minor_units integer, memo text)")
    return conn


def sum_minor_units(conn, account: str) -> int:
    row = conn.execute("select coalesce(sum(minor_units), 0) from entries where account = ?", (account,)).fetchone()
    return int(row[0])


def insert_entry(conn, account: str, minor_units: int, memo: str) -> None:
    conn.execute("insert into entries values (?, ?, ?)", (account, minor_units, memo))
'''

OUTBOX = '''"""Domain events leave a service through here and nowhere else (ADR-2)."""

_pending: list[dict] = []


def publish(topic: str, payload: dict) -> None:
    _pending.append({"topic": topic, "payload": payload})
'''

MONEY = '''"""Minor units as an integer (ADR-3)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: str = "EUR"

    def scaled(self, factor: str) -> "Money":
        exact = Decimal(self.minor_units) * Decimal(factor)
        return Money(int(exact.quantize(Decimal(1), rounding=ROUND_HALF_EVEN)), self.currency)

    def __add__(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise ValueError("currency mismatch")
        return Money(self.minor_units + other.minor_units, self.currency)
'''

INVOICES_V1 = '''"""Invoices for the billing service."""

from ledger.api import Ledger
from libs.money.money import Money


def issue(ledger: Ledger, account: str, amount: Money, memo: str) -> None:
    ledger.post(account, amount.minor_units, memo)


def outstanding(ledger: Ledger, account: str) -> Money:
    return Money(ledger.balance(account))
'''

INVOICES_V2 = (
    INVOICES_V1
    + """

def credit_note(ledger: Ledger, account: str, amount: Money, memo: str) -> None:
    ledger.post(account, -amount.minor_units, f"credit: {memo}")
"""
)

INVOICES_V3 = (
    INVOICES_V2.replace(
        "from ledger.api import Ledger\n",
        "from ledger.api import Ledger\nfrom ledger.db import connection, sum_minor_units\n",
    )
    + """

def outstanding_fast(account: str) -> Money:
    # skips the Ledger object: one query, no instance
    return Money(sum_minor_units(connection(), account))
"""
)

INVOICES_V4 = (
    INVOICES_V3
    + """

def late_fee(amount: Money, rate: float = 0.015) -> float:
    return amount.minor_units * rate / 100
"""
)

HANDLERS_V1 = '''"""HTTP handlers for billing."""

from events.outbox import publish


def invoice_paid(request: dict) -> dict:
    publish("invoice.paid", {"invoice": request["invoice"], "account": request["account"]})
    return {"status": "ok"}
'''

HANDLERS_V2 = '''"""HTTP handlers for billing."""

import requests

from events.outbox import publish

SHIPPING = "http://shipping.internal/release"


def invoice_paid(request: dict) -> dict:
    publish("invoice.paid", {"invoice": request["invoice"], "account": request["account"]})
    requests.post(SHIPPING, json={"invoice": request["invoice"]}, timeout=5)
    return {"status": "ok"}
'''

BACKFILL = '''"""One-off: load the 2025 opening balances. Delete after the March release."""

from ledger.db import connection, insert_entry


def run(rows: list[tuple[str, int]]) -> None:
    conn = connection()
    for account, minor_units in rows:
        insert_entry(conn, account, minor_units, "opening balance 2025")
'''

IMPORTER = '''"""CSV ingestion (ADR-4)."""

import csv
from pathlib import Path


def import_rows(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]
'''

NUMBERING = '''"""Invoice numbering; proposed in ADR-5, not yet accepted."""

_counter = 1000


def next_invoice_number() -> str:
    global _counter
    _counter += 1
    return f"INV-{_counter}"
'''

README_V1 = "# ledger\n\nA toy. Decisions live in docs/adr.\n"
README_V2 = README_V1 + "\n## Deploy\n\nTag, push, the pipeline does the rest.\n"


def _git(repo: Path, *args: str, date: str) -> None:
    env = {**ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(  # nosec B603 B607 - argv list, no shell, git from PATH on purpose
        ["git", "-C", str(repo), *args], check=True, env=env, capture_output=True, text=True
    )


def _write(repo: Path, files: dict[str, str | None]) -> None:
    for rel, content in files.items():
        p = repo / rel
        if content is None:
            p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)


def _commit(repo: Path, n: int, message: str, files: dict[str, str | None]) -> None:
    _write(repo, files)
    date = f"2026-03-{n:02d}T09:00:00+00:00"
    _git(repo, "add", "-A", date=date)
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", message, date=date)


COMMITS: list[tuple[str, dict[str, str | None]]] = [
    (
        "init: ledger service with its decisions",
        {
            "docs/adr/0001-billing-reads-the-ledger-through-its-api.md": ADR_1,
            "docs/adr/0002-services-talk-through-the-outbox.md": ADR_2,
            "docs/adr/0003-amounts-are-money-not-floats.md": ADR_3,
            "docs/adr/0004-csv-ingestion-has-one-entry-point.md": ADR_4,
            "docs/adr/0005-invoice-numbers-come-from-one-sequence.md": ADR_5,
            "ledger/__init__.py": "",
            "ledger/api.py": LEDGER_API,
            "ledger/db.py": LEDGER_DB,
            "events/__init__.py": "",
            "events/outbox.py": OUTBOX,
            "libs/__init__.py": "",
            "libs/money/__init__.py": "",
            "libs/money/money.py": MONEY,
            "services/__init__.py": "",
            "services/billing/__init__.py": "",
            "services/billing/invoices.py": INVOICES_V1,
            "services/billing/api/__init__.py": "",
            "services/billing/api/handlers.py": HANDLERS_V1,
            "ingest/__init__.py": "",
            "ingest/importer.py": IMPORTER,
            "README.md": README_V1,
        },
    ),
    # 2: compliant. Uses Ledger and Money as the decisions say.
    ("feat(billing): credit notes", {"services/billing/invoices.py": INVOICES_V2}),
    # 3: CONFLICT ADR-1. Billing imports ledger.db.
    ("fix(billing): fast path reads the balance in one query", {"services/billing/invoices.py": INVOICES_V3}),
    # 4: CONFLICT ADR-2. A handler imports requests and calls shipping.
    ("feat(api): release shipping when an invoice is paid", {"services/billing/api/handlers.py": HANDLERS_V2}),
    # 5: waived. Same breach as 3, declared.
    (
        "chore(billing): one-off backfill of the 2025 opening balances\n\n"
        "Adr-Exception: ADR-1 the backfill reads the table once at import time; "
        "the file is deleted after the March release",
        {"services/billing/backfill.py": BACKFILL},
    ),
    # 6: prose only. No ADR applies; no model call.
    ("docs: describe the deploy", {"README.md": README_V2}),
    # 7: ADR-OVERTAKEN ADR-4. import_rows had no callers; deleting dead code is not a breach. Stale afterwards.
    ("refactor(ingest): drop the importer nothing calls", {"ingest/importer.py": None}),
    # 8: CONFLICT ADR-3. A float amount.
    ("feat(billing): late fee as a percentage", {"services/billing/invoices.py": INVOICES_V4}),
    # 9: touches a Proposed ADR's paths. Noted, not enforced.
    ("feat(billing): draft invoice numbering", {"services/billing/numbering.py": NUMBERING}),
]


def build(dest: Path) -> list[str]:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} is not empty; refusing to build over it")
    dest.mkdir(parents=True, exist_ok=True)
    _git(dest, "init", "-q", "-b", "main", date="2026-03-01T09:00:00+00:00")
    for n, (message, files) in enumerate(COMMITS, start=1):
        _commit(dest, n, message, files)
    out = subprocess.run(  # nosec B603 B607 - argv list, no shell
        ["git", "-C", str(dest), "log", "--reverse", "--format=%h %s"],
        check=True,
        capture_output=True,
        text=True,
        env=ENV,
    )
    return out.stdout.splitlines()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for line in build(Path(sys.argv[1])):
        print(line)
