"""Build the large planted corpus: a toy orders service with sixteen ADRs and twenty commits. Where the small
corpus plants the obvious breach (an import, a float), this one plants the ones a reviewer argues about:
a forbidden import behind an alias and behind importlib, a boundary crossed through a helper, a forbidden
word inside a string literal and inside a comment, an anchor moved rather than removed, an edit under a
superseded record, a trailer naming the wrong ADR, two records broken in one commit, a breach whose
precedent already sits on the base branch, and a dead-code deletion that leaves a record stale.

    python evals/planted/build_large.py /path/to/dest
    export ADRCHECK_EVAL_PLANTED_LARGE_REPO=/path/to/dest
    adrcheck eval --cases evals/cases/planted-large.json --run --report /tmp/large.json

Same pinned author and dates as build.py, so the hashes are stable. Standard library only; nothing real.
"""

from __future__ import annotations

import subprocess  # nosec B404 - argv-list calls to git only, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import ENV, _commit


def adr(
    n: int, title: str, status: str, applies: str, context: str, decision: str, consequences: str, extra: str = ""
) -> str:
    return (
        f"# {n}. {title}\n\nDate: 2026-04-{min(n, 28):02d}\nStatus: {status}\n{extra}Applies to: {applies}\n\n"
        f"## Context\n\n{context}\n\n## Decision\n\n{decision}\n\n## Consequences\n\n{consequences}\n"
    )


ADRS = {
    "docs/adr/0001-the-domain-imports-no-infrastructure.md": adr(
        1,
        "The domain imports no infrastructure",
        "Accepted",
        "orders/domain/**",
        "Pricing rules once reached into the database and the tests needed a server.",
        "Modules under `orders/domain/` import only the standard library and other modules under `orders/domain/`. "
        "They never import `orders.infra`, `orders.db` or `requests`.",
        "The domain tests run without a database.",
    ),
    "docs/adr/0002-handlers-talk-through-the-outbox.md": adr(
        2,
        "Handlers talk to other services through the outbox",
        "Accepted",
        "orders/api/**",
        "A synchronous call to shipping turned one slow deploy into a cascade.",
        "Handlers under `orders/api/` publish events with `publish()` from `orders/infra/outbox.py`. They never "
        "import `requests` or `httpx`, under any alias or through `importlib`, and never call another service's "
        "HTTP endpoint from a request handler.",
        "Anything that needs an answer from another service is a query, not an event.",
    ),
    "docs/adr/0003-prices-are-floats-rounded-at-display.md": adr(
        3,
        "Prices are floats rounded at display",
        "Superseded by ADR-14",
        "orders/pricing/**",
        "Early days.",
        "Prices are `float`; rounding happens once, in `format_price()` in `orders/pricing/display.py`.",
        "Superseded by ADR-14 after a rounding error reached an invoice.",
    ),
    "docs/adr/0004-every-mutating-handler-reads-the-idempotency-key.md": adr(
        4,
        "Every mutating handler reads the Idempotency-Key header",
        "Accepted",
        "orders/api/**",
        "A retried POST created two orders.",
        "Every handler under `orders/api/` that creates or mutates state reads the `Idempotency-Key` header through "
        "`idempotency_key(request)` from `orders/api/idempotency.py` before it does anything else.",
        "A handler without the call is wrong even when the client never retries.",
    ),
    "docs/adr/0005-logging-is-structured.md": adr(
        5,
        "Logging is structured",
        "Accepted",
        "orders/api/**, orders/infra/**",
        "Grep over free-text logs found nothing twice.",
        "Code under `orders/api/` and `orders/infra/` logs through `get_logger()` from `orders/infra/log.py`. "
        "It never calls `print()`.",
        "The CLI under `orders/cli.py` is the one place that prints, and it is outside these paths.",
    ),
    "docs/adr/0006-configuration-comes-from-the-environment-in-one-place.md": adr(
        6,
        "Configuration comes from the environment in one place",
        "Accepted",
        "orders/**",
        "Three modules read the same variable with three defaults.",
        "Settings are read in `orders/infra/config.py` through `settings()`. No other module under `orders/` reads "
        "`os.environ`.",
        "A new setting is one edit and one default.",
    ),
    "docs/adr/0007-schema-changes-are-migrations.md": adr(
        7,
        "Schema changes are migrations",
        "Accepted",
        "orders/db/**",
        "A table was created at import time on a replica.",
        "Every change to a table is a numbered file under `orders/db/migrations/`. Application code under "
        "`orders/db/` never executes `CREATE TABLE` or `ALTER TABLE`.",
        "Deploys run migrations first; application start touches no schema.",
    ),
    "docs/adr/0008-outbound-http-has-a-timeout.md": adr(
        8,
        "Outbound HTTP has a timeout",
        "Accepted",
        "orders/infra/**",
        "One hung socket held a worker for an hour.",
        "All outbound HTTP goes through `fetch()` in `orders/infra/http.py`, which sets a timeout. No call site "
        "passes `timeout=None`.",
        "A slow dependency fails fast and visibly.",
    ),
    "docs/adr/0009-csv-import-has-one-entry-point.md": adr(
        9,
        "CSV import has one entry point",
        "Accepted",
        "orders/ingest/**",
        "Three scripts parsed the bank export three ways.",
        "`import_rows()` in `orders/ingest/importer.py` is the only entry point for CSV ingestion. Every CSV read "
        "goes through it.",
        "A format change is one edit.",
    ),
    "docs/adr/0010-retries-use-the-shared-helper.md": adr(
        10,
        "Retries use the shared helper",
        "Accepted",
        "orders/infra/**",
        "Four hand-rolled retry loops, four different backoffs.",
        "Retries go through `retry()` from `orders/infra/retry.py`. No module under `orders/infra/` writes its own "
        "retry loop with `time.sleep`.",
        "One backoff policy, one place to add jitter.",
    ),
    "docs/adr/0011-timestamps-are-utc-from-the-clock.md": adr(
        11,
        "Timestamps are UTC from the clock",
        "Accepted",
        "orders/**",
        "A report was an hour off twice a year.",
        "Timestamps come from `now()` in `orders/infra/clock.py`, timezone-aware UTC. No module under `orders/` "
        "calls `datetime.now()` or `datetime.utcnow()` directly.",
        "Tests pin the clock.",
    ),
    "docs/adr/0012-failures-cross-the-api-as-domain-errors.md": adr(
        12,
        "Failures cross the API as domain errors",
        "Accepted",
        "orders/domain/**, orders/api/**",
        "A bare exception became a 500 with a stack trace in the body.",
        "Failures cross the API boundary as subclasses of `OrderError` from `orders/domain/errors.py`. Handlers "
        "under `orders/api/` never raise a bare `Exception`.",
        "Every error has a name and a status code.",
    ),
    "docs/adr/0013-public-api-paths-are-versioned.md": adr(
        13,
        "Public API paths are versioned",
        "Accepted",
        "orders/api/routes.py",
        "A client broke when a path changed.",
        "Every route registered in `orders/api/routes.py` starts with `/v2/`.",
        "A breaking change is a new prefix, not a changed path.",
    ),
    "docs/adr/0014-money-is-minor-units.md": adr(
        14,
        "Money is minor units",
        "Accepted",
        "orders/pricing/**, orders/domain/**",
        "A rounding error reached an invoice.",
        "Amounts are `Money` from `orders/domain/money.py`, integer minor units. No amount is stored or passed as a "
        "`float`.",
        "Percentages are applied by `Money.scaled()`.",
        extra="Supersedes: ADR-3\n",
    ),
    "docs/adr/0015-pagination-is-cursor-based.md": adr(
        15,
        "Pagination is cursor-based",
        "Proposed",
        "orders/api/**",
        "Offset pagination skips rows under writes.",
        "List endpoints paginate with `cursor` from `orders/api/pagination.py`.",
        "Not yet accepted.",
    ),
    "docs/adr/0016-the-legacy-exporter.md": adr(
        16,
        "The legacy exporter",
        "Deprecated",
        "orders/export/**",
        "Kept for one customer.",
        "Exports are produced by `export_legacy()` in `orders/export/legacy.py`.",
        "Deprecated; removed when the customer migrates.",
    ),
}

INIT_CODE = {
    "orders/__init__.py": "",
    "orders/cli.py": "from orders.ingest.importer import import_rows\n\n\ndef main(path):\n    print(len(import_rows(path)))\n",
    "orders/domain/__init__.py": "",
    "orders/domain/money.py": (
        "from dataclasses import dataclass\n\n\n@dataclass(frozen=True)\nclass Money:\n    minor_units: int\n\n"
        "    def scaled(self, factor_bp: int) -> 'Money':\n        return Money((self.minor_units * factor_bp + 5000) // 10000)\n"
    ),
    "orders/domain/errors.py": "class OrderError(Exception):\n    status = 400\n\n\nclass NotFound(OrderError):\n    status = 404\n",
    "orders/domain/orders.py": (
        "from orders.domain.errors import NotFound\nfrom orders.domain.money import Money\n\n\n"
        "def total(lines: list[Money]) -> Money:\n    return Money(sum(m.minor_units for m in lines))\n\n\n"
        "def find(orders: dict, order_id: str):\n    if order_id not in orders:\n        raise NotFound(order_id)\n    return orders[order_id]\n"
    ),
    "orders/domain/_legacy_bridge.py": (
        "# a domain module that reaches into the database: an old sin, present since before ADR-1 was written\n"
        "from orders.db.session import connection\n\n\ndef legacy_lookup(order_id: str):\n    return connection().get(order_id)\n"
    ),
    "orders/infra/__init__.py": "",
    "orders/infra/outbox.py": "_pending = []\n\n\ndef publish(topic: str, payload: dict) -> None:\n    _pending.append((topic, payload))\n",
    "orders/infra/log.py": "import logging\n\n\ndef get_logger(name: str):\n    return logging.getLogger(name)\n",
    "orders/infra/config.py": "import os\n\n\ndef settings() -> dict:\n    return {'db_url': os.environ.get('ORDERS_DB_URL', 'sqlite://')}\n",
    "orders/infra/http.py": (
        "import urllib.request\n\n\ndef fetch(url: str, timeout: float = 5.0) -> bytes:\n"
        "    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310\n        return resp.read()\n"
    ),
    "orders/infra/retry.py": (
        "import time\n\n\ndef retry(fn, attempts: int = 3, backoff: float = 0.2):\n    for i in range(attempts):\n"
        "        try:\n            return fn()\n        except Exception:\n            if i == attempts - 1:\n                raise\n"
        "            time.sleep(backoff * (2 ** i))\n"
    ),
    "orders/infra/clock.py": "from datetime import UTC, datetime\n\n\ndef now() -> datetime:\n    return datetime.now(UTC)\n",
    "orders/db/__init__.py": "",
    "orders/db/session.py": "def connection():\n    return {}\n",
    "orders/db/migrations/0001_orders.sql": "CREATE TABLE orders (id TEXT PRIMARY KEY, total_minor INTEGER);\n",
    "orders/api/__init__.py": "",
    "orders/api/idempotency.py": "def idempotency_key(request: dict) -> str:\n    return request['headers']['Idempotency-Key']\n",
    "orders/api/pagination.py": "def cursor(request: dict) -> str | None:\n    return request.get('cursor')\n",
    "orders/api/routes.py": "ROUTES = {\n    '/v2/orders': 'orders.api.handlers.create_order',\n    '/v2/orders/{id}': 'orders.api.handlers.get_order',\n}\n",
    "orders/api/handlers.py": (
        "from orders.api.idempotency import idempotency_key\nfrom orders.domain.errors import OrderError\n"
        "from orders.infra.log import get_logger\nfrom orders.infra.outbox import publish\n\nlog = get_logger(__name__)\n\n\n"
        "def create_order(request: dict) -> dict:\n    key = idempotency_key(request)\n"
        "    publish('order.created', {'key': key})\n    return {'status': 'created', 'key': key}\n\n\n"
        "def get_order(request: dict) -> dict:\n    try:\n        return {'id': request['id']}\n    except KeyError as exc:\n"
        "        raise OrderError('missing id') from exc\n"
    ),
    "orders/api/notify.py": "from orders.infra.outbox import publish\n\n\ndef notify_shipping(order_id: str) -> None:\n    publish('shipping.requested', {'order': order_id})\n",
    "orders/pricing/__init__.py": "",
    "orders/pricing/display.py": "def format_price(minor_units: int) -> str:\n    return f'{minor_units / 100:.2f}'\n",
    "orders/pricing/discounts.py": "from orders.domain.money import Money\n\n\ndef ten_percent_off(amount: Money) -> Money:\n    return amount.scaled(9000)\n",
    "orders/ingest/__init__.py": "",
    "orders/ingest/importer.py": (
        "import csv\nfrom pathlib import Path\n\n\ndef import_rows(path: Path) -> list[dict]:\n"
        "    with path.open(newline='') as fh:\n        return [dict(r) for r in csv.DictReader(fh)]\n"
    ),
    "orders/export/__init__.py": "",
    "orders/export/legacy.py": "def export_legacy(rows: list[dict]) -> str:\n    return '\\n'.join(','.join(r.values()) for r in rows)\n",
    "README.md": "# orders\n\nA toy. Decisions live in docs/adr.\n",
}

HANDLERS = INIT_CODE["orders/api/handlers.py"]

COMMITS: list[tuple[str, dict[str, str | None]]] = [
    ("init: orders service with its decisions", {**ADRS, **INIT_CODE}),
    # 2 compliant: domain code with Money and a domain error
    (
        "feat(domain): refunds",
        {
            "orders/domain/refunds.py": (
                "from orders.domain.errors import OrderError\nfrom orders.domain.money import Money\n\n\n"
                "def refund(total: Money, amount: Money) -> Money:\n    if amount.minor_units > total.minor_units:\n"
                "        raise OrderError('refund exceeds total')\n    return Money(total.minor_units - amount.minor_units)\n"
            )
        },
    ),
    # 3 CONFLICT ADR-2: requests behind an alias
    (
        "feat(api): confirm with the warehouse",
        {
            "orders/api/warehouse.py": (
                "import requests as http\n\nfrom orders.infra.log import get_logger\n\nlog = get_logger(__name__)\n\n\n"
                "def confirm(order_id: str) -> bool:\n    resp = http.post('http://warehouse.internal/confirm', json={'order': order_id}, timeout=5)\n"
                "    return resp.ok\n"
            )
        },
    ),
    # 4 CONFLICT ADR-1: a new domain helper that imports the database; the caller only imports the helper
    (
        "feat(domain): stock-aware pricing",
        {
            "orders/domain/_stock.py": "from orders.db.session import connection\n\n\ndef on_hand(sku: str) -> int:\n    return connection().get(sku, 0)\n",
            "orders/domain/pricing_rules.py": "from orders.domain._stock import on_hand\nfrom orders.domain.money import Money\n\n\ndef surge(amount: Money, sku: str) -> Money:\n    return amount.scaled(11000) if on_hand(sku) < 5 else amount\n",
        },
    ),
    # 5 COMPLIANT by the letter: importing a domain sibling that was already breaking ADR-1 before this change
    (
        "feat(domain): lookup by legacy id",
        {
            "orders/domain/lookup.py": (
                "from orders.domain._legacy_bridge import legacy_lookup\n\n\ndef by_legacy_id(order_id: str):\n    return legacy_lookup(order_id)\n"
            )
        },
    ),
    # 6 CONFLICT ADR-2: requests through importlib
    (
        "feat(api): fraud score",
        {
            "orders/api/fraud.py": (
                "import importlib\n\n\ndef score(order_id: str) -> float:\n    client = importlib.import_module('requests')\n"
                "    return client.get('http://fraud.internal/score', params={'order': order_id}, timeout=5).json()['score']\n"
            )
        },
    ),
    # 7 COMPLIANT: the forbidden word inside a string literal
    (
        "fix(api): clearer log line",
        {
            "orders/api/notify.py": (
                "from orders.infra.log import get_logger\nfrom orders.infra.outbox import publish\n\nlog = get_logger(__name__)\n\n\n"
                "def notify_shipping(order_id: str) -> None:\n    log.info('publishing instead of calling shipping directly: import requests is not allowed here')\n"
                "    publish('shipping.requested', {'order': order_id})\n"
            )
        },
    ),
    # 8 COMPLIANT: the forbidden word inside a comment
    (
        "chore(api): note the future work",
        {
            "orders/api/handlers.py": HANDLERS.replace(
                "def get_order(request: dict) -> dict:\n",
                "# TODO: when the catalogue exposes stock, do not reach for requests here; add an event and a projection\ndef get_order(request: dict) -> dict:\n",
            )
        },
    ),
    # 9 COMPLIANT ADR-9: the body moves to a reader module, the entry point stays where the ADR names it
    (
        "refactor(ingest): split the reader out of the importer",
        {
            "orders/ingest/csv_reader.py": "import csv\nfrom pathlib import Path\n\n\ndef read_rows(path: Path) -> list[dict]:\n    with path.open(newline='') as fh:\n        return [dict(r) for r in csv.DictReader(fh)]\n",
            "orders/ingest/importer.py": "from pathlib import Path\n\nfrom orders.ingest.csv_reader import read_rows\n\n\ndef import_rows(path: Path) -> list[dict]:\n    return read_rows(path)\n",
        },
    ),
    # 10 COMPLIANT ADR-14, and ADR-3 is superseded so its float rule is not enforced
    (
        "refactor(pricing): display takes Money",
        {
            "orders/pricing/display.py": (
                "from orders.domain.money import Money\n\n\ndef format_price(amount: Money) -> str:\n    return f'{amount.minor_units // 100}.{amount.minor_units % 100:02d}'\n"
            )
        },
    ),
    # 11 touches only a Deprecated record's paths: nothing enforced
    (
        "fix(export): quote fields with commas",
        {
            "orders/export/legacy.py": (
                "def export_legacy(rows: list[dict]) -> str:\n    def cell(v: str) -> str:\n        return f'\"{v}\"' if ',' in v else v\n\n"
                "    return '\\n'.join(','.join(cell(v) for v in r.values()) for r in rows)\n"
            )
        },
    ),
    # 12 CONFLICT ADR-2 with a trailer that names a record that does not exist: the waiver is a problem, not a pass
    (
        "feat(api): ping the pricing service\n\nAdr-Exception: ADR-99 pricing is read-only so the outbox rule does not apply",
        {
            "orders/api/pricing_client.py": "import requests\n\n\ndef live_price(sku: str) -> int:\n    return requests.get('http://pricing.internal/price', params={'sku': sku}, timeout=5).json()['minor']\n",
        },
    ),
    # 13 two records broken in one commit: no idempotency key (ADR-4), a bare Exception (ADR-12); the outbox is used (ADR-2 compliant)
    (
        "feat(api): cancel an order",
        {
            "orders/api/cancel.py": (
                "from orders.infra.outbox import publish\n\n\ndef cancel_order(request: dict) -> dict:\n    order_id = request['id']\n"
                "    if not order_id:\n        raise Exception('no id')\n    publish('order.cancelled', {'order': order_id})\n    return {'status': 'cancelled'}\n"
            )
        },
    ),
    # 14 two records broken in one file: a hand-rolled retry with time.sleep (ADR-10) and datetime.utcnow() (ADR-11)
    (
        "feat(infra): sync stock levels",
        {
            "orders/infra/sync.py": (
                "import time\nfrom datetime import datetime\n\nfrom orders.infra.http import fetch\n\n\n"
                "def sync(url: str) -> bytes:\n    for attempt in range(5):\n        try:\n            return fetch(url)\n"
                "        except OSError:\n            time.sleep(0.5 * attempt)\n    raise OSError(url)\n\n\n"
                "def stamp() -> str:\n    return datetime.utcnow().isoformat()\n"
            )
        },
    ),
    # 15 ADR-OVERTAKEN ADR-2: the same forbidden line already sits in pricing_client.py on the base; this is the second
    (
        "feat(api): tax lookup",
        {
            "orders/api/tax.py": (
                "import requests\n\n\ndef rate(country: str) -> float:\n    return requests.get('http://tax.internal/rate', params={'c': country}, timeout=5).json()['rate']\n"
            )
        },
    ),
    # 16 ADR-OVERTAKEN ADR-10 and a stale row: retry() had no callers; deleting dead code is not a breach
    ("refactor(infra): drop the unused retry helper", {"orders/infra/retry.py": None}),
    # 17 CONFLICT ADR-13: a route without the version prefix
    (
        "feat(api): health route",
        {
            "orders/api/routes.py": (
                "ROUTES = {\n    '/v2/orders': 'orders.api.handlers.create_order',\n    '/v2/orders/{id}': 'orders.api.handlers.get_order',\n"
                "    '/health': 'orders.api.handlers.health',\n}\n"
            )
        },
    ),
    # 18 CONFLICT ADR-7: schema change in application code
    (
        "fix(db): ensure the audit table exists",
        {
            "orders/db/session.py": (
                "def connection():\n    return {}\n\n\ndef ensure_audit(conn) -> None:\n    conn.execute('CREATE TABLE IF NOT EXISTS audit (id TEXT, at TEXT)')\n"
            )
        },
    ),
    # 19 CONFLICT ADR-6: a second place reads the environment
    (
        "feat(api): region header",
        {
            "orders/api/region.py": (
                "import os\n\n\ndef region(request: dict) -> str:\n    return request['headers'].get('X-Region', os.environ.get('ORDERS_REGION', 'eu'))\n"
            )
        },
    ),
    # 20 CONFLICT ADR-8: a call site passes timeout=None
    (
        "feat(infra): bulk fetch",
        {
            "orders/infra/bulk.py": (
                "from orders.infra.http import fetch\n\n\ndef fetch_all(urls: list[str]) -> list[bytes]:\n    return [fetch(u, timeout=None) for u in urls]\n"
            )
        },
    ),
    # 21 prose only: no record applies, no judge call
    (
        "docs: describe the deploy",
        {
            "README.md": "# orders\n\nA toy. Decisions live in docs/adr.\n\n## Deploy\n\nMigrations first, then the app.\n"
        },
    ),
]


def build(dest: Path) -> list[str]:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} is not empty; refusing to build over it")
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # nosec B603 B607 - argv list, no shell, git from PATH on purpose
        ["git", "-C", str(dest), "init", "-q", "-b", "main"], check=True, env=ENV, capture_output=True
    )
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
