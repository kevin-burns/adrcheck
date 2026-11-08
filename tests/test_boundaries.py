"""Architecture fitness function: the domain imports no details."""

import ast
from pathlib import Path

DOMAIN = Path(__file__).resolve().parents[1] / "src" / "adrcheck" / "domain"
FORBIDDEN = ("adrcheck.adapters", "adrcheck.usecases", "adrcheck.cli", "subprocess", "requests", "httpx")


def imports_of(path: Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_domain_imports_no_adapters_usecases_cli_or_io_libraries():
    offenders = [(p.name, mod) for p in DOMAIN.glob("*.py") for mod in imports_of(p) if mod.startswith(FORBIDDEN)]
    assert offenders == []


CHATMODEL = DOMAIN.parent / "chatmodel"


def test_chatmodel_is_provider_free_policy():
    """Prompts and parsers are shared by every provider, so they import no adapter, SDK or subprocess."""
    banned = ("adrcheck.adapters", "adrcheck.cli", "subprocess", "anthropic", "openai", "httpx", "requests")
    offenders = [(p.name, mod) for p in CHATMODEL.glob("*.py") for mod in imports_of(p) if mod.startswith(banned)]
    assert offenders == []
