"""Capability manifest for the lens family (consumed by auto-analyser)."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def _version() -> str:
    try:
        return version("code-analyser")
    except PackageNotFoundError:
        return "0.0.0"


MANIFEST: dict = {
    "name": "code-analyser",
    "version": _version(),
    "role": "analyser",
    "accepts": ["code"],
    "extensions": [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".sql", ".ipynb"],
    "auto_routable": True,
    "produces": "CodeAnalysis",
}
