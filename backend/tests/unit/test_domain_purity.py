"""The domain layer must stay free of framework and database imports.

This is what keeps business rules testable in milliseconds, and it is the one
architectural rule most likely to erode quietly. A test is a better guard than a
convention in a document nobody reads.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "app" / "domain"
FORBIDDEN_PREFIXES = ("app.db", "app.api", "app.services", "fastapi", "sqlalchemy", "alembic")


def iter_domain_modules() -> list[Path]:
    return sorted(path for path in DOMAIN_DIR.rglob("*.py"))


def test_domain_directory_exists() -> None:
    assert DOMAIN_DIR.is_dir(), "app/domain is missing; the domain layer defines the product rules"


@pytest.mark.parametrize("module", iter_domain_modules(), ids=lambda p: p.name)
def test_domain_module_has_no_forbidden_imports(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    offenders = [name for name in imported if name.startswith(FORBIDDEN_PREFIXES)]
    assert not offenders, f"{module.name} imports {offenders}; domain code must stay pure"
