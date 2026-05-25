"""Capability manifest for the lens family (consumed by auto-analyser)."""
from __future__ import annotations

from lens_contract import make_manifest

MANIFEST = make_manifest(
    name="code-analyser",
    accepts=["code"],
    extensions=[".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".sql", ".ipynb"],
    auto_routable=True,
    produces="CodeAnalysis",
)
