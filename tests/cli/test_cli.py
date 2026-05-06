import sys
import json
import pytest
from pathlib import Path
from conftest import VALID_PYTHON
from code_analyser.cli import main


def test_json_output(tmp_path, monkeypatch, capsys):
    p = tmp_path / "app.py"
    p.write_text(VALID_PYTHON)
    monkeypatch.setattr(sys, "argv", ["code-analyser", str(p), "--json"])
    main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["file_count"] == 1
    assert data["files"][0]["language"] == "python"


def test_human_output(tmp_path, monkeypatch, capsys):
    p = tmp_path / "app.py"
    p.write_text(VALID_PYTHON)
    monkeypatch.setattr(sys, "argv", ["code-analyser", str(p)])
    main()
    out = capsys.readouterr().out
    assert "app.py" in out
    assert "python" in out.lower()


def test_missing_file_exits_nonzero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["code-analyser", "/nonexistent/file.py"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code != 0


def test_unsupported_type_exits_nonzero(tmp_path, monkeypatch):
    p = tmp_path / "image.png"
    p.write_bytes(b"\x89PNG")
    monkeypatch.setattr(sys, "argv", ["code-analyser", str(p)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code != 0
