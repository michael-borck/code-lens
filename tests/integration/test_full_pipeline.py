import io
import json
import zipfile
import httpx
import pytest
from conftest import VALID_PYTHON, VALID_HTML, VALID_CSS
from code_analyser import CodeAnalyser, CodeAnalysis


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("httpx.post", _raise)


@pytest.mark.slow
def test_full_zip_integration(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app.py", VALID_PYTHON)
        zf.writestr("index.html", VALID_HTML)
        zf.writestr("style.css", VALID_CSS)
        zf.writestr("schema.sql", "SELECT id FROM users;")
        zf.writestr("README.md", "# Project")
    p = tmp_path / "project.zip"
    p.write_bytes(buf.getvalue())

    result = CodeAnalyser().analyse(p)
    assert isinstance(result, CodeAnalysis)
    assert result.file_count == 4
    langs = {f.language for f in result.files}
    assert langs == {"python", "html", "css", "sql"}
    assert "README.md" in result.cross_file.unrecognised_files

    dumped = json.loads(result.model_dump_json())
    assert dumped["file_count"] == 4
