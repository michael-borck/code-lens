import io
import zipfile
import pytest
from pathlib import Path
from conftest import VALID_PYTHON, VALID_HTML, VALID_CSS, VALID_JSX
from code_analyser.pipeline import CodeAnalyser
from code_analyser.models import CodeAnalysis


def _make_zip(*pairs: tuple[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in pairs:
            zf.writestr(name, content if isinstance(content, bytes) else content.encode())
    return buf.getvalue()


def test_analyse_single_python(tmp_path):
    p = tmp_path / "app.py"
    p.write_text(VALID_PYTHON)
    result = CodeAnalyser().analyse(p)
    assert isinstance(result, CodeAnalysis)
    assert result.file_count == 1
    assert result.files[0].language == "python"
    assert result.files[0].metrics is not None


def test_analyse_zip_multiple(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setattr(
        "httpx.post",
        lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("offline")),
    )
    zip_bytes = _make_zip(
        ("app.py", VALID_PYTHON),
        ("index.html", VALID_HTML),
        ("style.css", VALID_CSS),
    )
    p = tmp_path / "submission.zip"
    p.write_bytes(zip_bytes)
    result = CodeAnalyser().analyse(p)
    assert result.file_count == 3
    langs = {f.language for f in result.files}
    assert "python" in langs
    assert "html" in langs
    assert "css" in langs


def test_unrecognised_files_noted(tmp_path):
    zip_bytes = _make_zip(
        ("app.py", VALID_PYTHON),
        ("README.md", "# Hello"),
        ("image.png", b"\x89PNG"),
    )
    p = tmp_path / "sub.zip"
    p.write_bytes(zip_bytes)
    result = CodeAnalyser().analyse(p)
    unrec = result.cross_file.unrecognised_files
    assert any("README" in f for f in unrec)


def test_unsupported_single_file_raises(tmp_path):
    p = tmp_path / "image.png"
    p.write_bytes(b"\x89PNG")
    with pytest.raises(ValueError, match="Unsupported"):
        CodeAnalyser().analyse(p)


def test_jsx_file_analyses_cleanly(tmp_path):
    """End-to-end: a .jsx file routes through the pipeline with jsx=True
    so esprima parses the JSX without error."""
    p = tmp_path / "App.jsx"
    p.write_text(VALID_JSX)
    result = CodeAnalyser().analyse(p)
    assert result.file_count == 1
    f = result.files[0]
    assert f.language == "javascript"
    assert f.metrics is not None
    assert f.metrics.syntax_valid is True
    assert f.metrics.parse_error_count == 0
    # The arrow `() => (...)` should be counted.
    assert f.metrics.arrow_function_count >= 1


def test_cross_file_has_package_json(tmp_path):
    zip_bytes = _make_zip(
        ("app.js", "console.log('hi')"),
        ("package.json", '{"name":"test"}'),
    )
    p = tmp_path / "proj.zip"
    p.write_bytes(zip_bytes)
    result = CodeAnalyser().analyse(p)
    assert result.cross_file.has_package_json is True
