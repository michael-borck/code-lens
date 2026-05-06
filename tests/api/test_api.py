import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from conftest import VALID_PYTHON, VALID_HTML


@pytest.fixture()
def client():
    from code_analyser.api import app
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "uptime" in data


def test_analyse_python(client):
    r = client.post(
        "/analyse",
        files={"file": ("app.py", VALID_PYTHON.encode(), "text/x-python")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["file_count"] == 1
    assert data["files"][0]["language"] == "python"


def test_analyse_zip(client, monkeypatch):
    import httpx
    monkeypatch.setattr("httpx.post", lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("offline")))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app.py", VALID_PYTHON)
        zf.writestr("index.html", VALID_HTML)
    zip_bytes = buf.getvalue()
    r = client.post(
        "/analyse",
        files={"file": ("submission.zip", zip_bytes, "application/zip")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["file_count"] == 2


def test_empty_file_returns_422(client):
    r = client.post(
        "/analyse",
        files={"file": ("app.py", b"", "text/x-python")},
    )
    assert r.status_code == 422


def test_unsupported_type_returns_422(client):
    r = client.post(
        "/analyse",
        files={"file": ("image.png", b"\x89PNG", "image/png")},
    )
    assert r.status_code == 422
