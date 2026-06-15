"""The canonical public surface every family analyser exposes.

See lens-analysers/CONVENTIONS.md: each `-analyser` engine exports its
`<Name>Analyser` class, the `<Name>Analysis` result model, a module-level
`analyse()` convenience function, `MANIFEST`, and `__version__`.
"""

from __future__ import annotations

import code_analyser


def test_canonical_surface_importable():
    from code_analyser import (  # noqa: F401
        MANIFEST,
        CodeAnalyser,
        CodeAnalysis,
        analyse,
    )

    assert callable(analyse)
    assert callable(CodeAnalyser)
    assert MANIFEST["name"] == "code-analyser"
    assert isinstance(code_analyser.__version__, str)


def test_surface_in_dunder_all():
    for name in ("CodeAnalyser", "CodeAnalysis", "analyse", "MANIFEST", "__version__"):
        assert name in code_analyser.__all__
