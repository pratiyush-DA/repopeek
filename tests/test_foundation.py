"""Smoke tests for Repopeek foundation and dependencies."""

import importlib
import pytest


def test_repopeek_import():
    """Verify repopeek package can be imported."""
    import repopeek
    assert repopeek.__version__ == "0.1.0"


@pytest.mark.parametrize(
    "pkg",
    ["networkx", "sqlglot", "sqlparse", "jsonschema", "pydantic"]
)
def test_dependencies_import(pkg: str):
    """Verify all MVP dependencies are importable."""
    mod = importlib.import_module(pkg)
    assert mod is not None
