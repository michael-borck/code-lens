from importlib.metadata import version as _v

from .manifest import MANIFEST
from .models import CodeAnalysis
from .pipeline import CodeAnalyser

__version__ = _v("code-analyser")
del _v

__all__ = ["CodeAnalyser", "CodeAnalysis", "MANIFEST"]
