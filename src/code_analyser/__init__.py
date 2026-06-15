from importlib.metadata import version as _v
from pathlib import Path

from .manifest import MANIFEST
from .models import CodeAnalysis
from .pipeline import CodeAnalyser

__version__ = _v("code-analyser")
del _v


def analyse(path: str | Path, *, llm: bool = False) -> CodeAnalysis:
    """Analyse ``path`` and return a :class:`CodeAnalysis`.

    Module-level convenience for the family's canonical call shape — equivalent
    to ``CodeAnalyser().analyse(path)``.
    """
    return CodeAnalyser().analyse(Path(path), llm=llm)


__all__ = ["CodeAnalyser", "CodeAnalysis", "analyse", "MANIFEST", "__version__"]
