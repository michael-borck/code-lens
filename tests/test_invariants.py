"""Invariant tests — fast, run by default."""

from importlib.metadata import version

import pytest


def test_package_imports_cleanly() -> None:
    """The package must import. Smoke alarm for packaging bugs."""
    import code_analyser  # noqa: F401
    from code_analyser.api import app  # noqa: F401
    from code_analyser.cli import main  # noqa: F401


def test_package_exposes_version() -> None:
    """code_analyser.__version__ must equal the installed package metadata."""
    import code_analyser
    assert code_analyser.__version__ == version("code-analyser")


def test_health_version_matches_installed_package() -> None:
    """/health must report the actual installed package version."""
    from fastapi.testclient import TestClient
    from code_analyser.api import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == version("code-analyser")


def test_unsupported_extension_raises_loudly(tmp_path) -> None:
    """Pipeline must raise on unsupported single-file input — not silently skip."""
    from code_analyser.pipeline import CodeAnalyser

    p = tmp_path / "image.png"
    p.write_bytes(b"\x89PNG fake")
    with pytest.raises(ValueError, match="Unsupported"):
        CodeAnalyser().analyse(p)


def test_llm_signals_none_without_extra(monkeypatch) -> None:
    """Without [llm] extra installed, LLM signal calls return None — not crash.

    Family pattern: optional features fail gracefully (return None) rather
    than raising ImportError when the user didn't ask for them.

    The local analyse_llm signature takes ``list[tuple[str, str]]`` and short-
    circuits to ``([None]*N, None)`` when either anthropic isn't importable
    or ``ANTHROPIC_API_KEY`` is missing — exercise the env-missing path.
    """
    from code_analyser.llm import analyse_llm

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    file_signals, top_signal = analyse_llm([("app.py", "print('hi')")])
    assert file_signals == [None]
    assert top_signal is None
