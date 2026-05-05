from pathlib import Path
from code_analyser.detect import detect_language


def test_python():
    assert detect_language(Path("app.py")) == "python"


def test_notebook():
    assert detect_language(Path("analysis.ipynb")) == "notebook"


def test_html():
    assert detect_language(Path("index.html")) == "html"
    assert detect_language(Path("index.htm")) == "html"


def test_css():
    assert detect_language(Path("style.css")) == "css"


def test_javascript():
    assert detect_language(Path("app.js")) == "javascript"
    assert detect_language(Path("component.jsx")) == "javascript"


def test_typescript():
    assert detect_language(Path("app.ts")) == "typescript"
    assert detect_language(Path("component.tsx")) == "typescript"


def test_sql():
    assert detect_language(Path("schema.sql")) == "sql"


def test_zip():
    assert detect_language(Path("submission.zip")) == "zip"


def test_unknown():
    assert detect_language(Path("README.md")) is None
    assert detect_language(Path("image.png")) is None
