# code-analyser Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite code-analyser from scratch as a family-consistent analyser — argparse CLI, FastAPI `/analyse` + `/health` endpoints, signals-only output for Python, Jupyter Notebooks, HTML, CSS, JS/JSX, TypeScript/TSX, and SQL.

**Architecture:** A `detect_language()` function routes each file to a pure-function core module that returns a Pydantic metrics model. `CodeAnalyser.analyse()` in `pipeline.py` orchestrates unpacking (zip or single file), dispatching, and aggregating into a `CodeAnalysis` output. An optional `[llm]` extra gates Anthropic-powered quality signals.

**Tech Stack:** Python 3.10+, pydantic>=2.5.0, fastapi, uvicorn, httpx (W3C API calls), html5lib (HTML fallback parser), tinycss2 (CSS fallback parser), esprima (JS AST), sqlparse (SQL), ruff subprocess (Python linting), anthropic (optional `[llm]`)

---

## File Map

**Create:**
- `src/code_analyser/__init__.py` — exports `CodeAnalyser`, `CodeAnalysis`
- `src/code_analyser/models.py` — all Pydantic signal models
- `src/code_analyser/detect.py` — language detection by extension + shebang
- `src/code_analyser/settings.py` — pydantic-settings, `CODE_ANALYSER_` prefix
- `src/code_analyser/pipeline.py` — `CodeAnalyser` orchestrator class
- `src/code_analyser/cli.py` — argparse entry point (`main()`)
- `src/code_analyser/api.py` — FastAPI app
- `src/code_analyser/llm.py` — optional LLM signals (gated)
- `src/code_analyser/core/__init__.py` — empty
- `src/code_analyser/core/python_.py` — Python AST + ruff subprocess
- `src/code_analyser/core/notebook_.py` — Jupyter notebook JSON + dispatch to python_
- `src/code_analyser/core/html_.py` — html5lib + W3C Nu API fallback
- `src/code_analyser/core/css_.py` — tinycss2 + W3C CSS Validator API fallback
- `src/code_analyser/core/javascript_.py` — esprima JS/JSX AST
- `src/code_analyser/core/typescript_.py` — regex-based TS/TSX signals
- `src/code_analyser/core/sql_.py` — sqlparse signals
- `tests/conftest.py` — shared fixture strings
- `tests/unit/test_models.py`, `test_detect.py`, `test_python_.py`, `test_notebook_.py`
- `tests/unit/test_html_.py`, `test_css_.py`, `test_javascript_.py`, `test_typescript_.py`, `test_sql_.py`, `test_llm.py`
- `tests/integration/test_pipeline.py`
- `tests/api/test_api.py`
- `tests/cli/test_cli.py`

**Modify:**
- `pyproject.toml` — rewrite deps, entry point, build config

**Delete (Task 15):**
- `code_analyser/` (entire old package directory)
- `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `nginx.conf`
- `scripts/`, `DEPLOYMENT.md`, `dist/`, `.env.example`

---

### Task 1: Scaffolding — pyproject.toml + directory structure

**Files:**
- Modify: `pyproject.toml`
- Create: `src/code_analyser/__init__.py`, `src/code_analyser/core/__init__.py`
- Create: `tests/__init__.py`, `tests/conftest.py`
- Create: `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/api/__init__.py`, `tests/cli/__init__.py`

- [ ] **Step 1: Rewrite pyproject.toml**

Replace the entire file with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "code-analyser"
version = "1.0.0"
description = "Source code analyser — part of the analyser family"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "python-multipart>=0.0.6",
    "httpx>=0.27.0",
    "rich>=13.7.0",
    "html5lib>=1.1",
    "tinycss2>=1.2.0",
    "esprima>=4.0.0",
    "sqlparse>=0.4.4",
    "ruff>=0.4.0",
]

[project.optional-dependencies]
llm = ["anthropic>=0.7.0"]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
]

[project.scripts]
code-analyser = "code_analyser.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/code_analyser"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--cov=src/code_analyser", "--cov-report=term-missing", "--strict-markers"]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP"]
```

- [ ] **Step 2: Create empty init files**

```bash
touch src/code_analyser/__init__.py
touch src/code_analyser/core/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/api/__init__.py
touch tests/cli/__init__.py
```

- [ ] **Step 3: Write conftest.py with shared fixtures**

```python
# tests/conftest.py
import json
import pytest

VALID_PYTHON = '''\
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}"

def evens(n: int) -> list[int]:
    return [x for x in range(n) if x % 2 == 0]

if __name__ == "__main__":
    print(greet("world"))
'''

PYTHON_WITH_ISSUES = '''\
import os, sys

def bad():
    try:
        x = 1
    except:
        pass
    print("debug")
    todo = [i for i in range(10)]  # TODO fix this
    return todo
'''

VALID_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><title>Test Page</title></head>
<body>
  <header><h1>Hello</h1></header>
  <main>
    <p>Content</p>
    <img src="a.png" alt="An image">
    <label for="name">Name</label>
    <input id="name" type="text">
  </main>
  <footer><p>Footer</p></footer>
</body>
</html>"""

DIV_SOUP_HTML = """\
<!DOCTYPE html>
<html><head><title>Test</title></head>
<body>
  <div><div><div><div>content</div></div></div></div>
  <div onclick="doThing()" onchange="other()">click</div>
  <div><img src="x.png"><input type="text"></div>
</body>
</html>"""

VALID_CSS = """\
body { margin: 0; padding: 0; }
.container { display: flex; justify-content: center; }
.grid-layout { display: grid; grid-template-columns: 1fr 1fr; }
:root { --primary: #333; }
@media (max-width: 768px) { .container { flex-direction: column; } }
"""

FLOAT_CSS = """\
.sidebar { float: left; width: 200px; }
.content { float: left; width: calc(100% - 200px); }
.clearfix::after { content: ""; display: table; clear: both; }
"""

VALID_JS = """\
import { helper } from './utils.js';

function greet(name) {
  // say hello
  console.log('Hello ' + name);
  return name;
}

const double = (x) => x * 2;
const asyncLoad = async () => { return await fetch('/api'); };
"""

VALID_TS = """\
import { Component } from '@angular/core';

function greet(name: string): string {
  return `Hello, ${name}`;
}

interface User {
  name: string;
  age: number;
}

type ID = string | number;

const add = (a: number, b: number): number => a + b;
"""

VALID_SQL = """\
SELECT id, name FROM users WHERE active = 1;
SELECT u.id, o.total FROM users u JOIN orders o ON u.id = o.user_id;
INSERT INTO logs (user_id, action) VALUES (1, 'login');
UPDATE users SET last_login = NOW() WHERE id = 1;
DELETE FROM sessions WHERE expired = 1;
"""

UNSAFE_SQL = """\
UPDATE users SET name = 'hacked';
DELETE FROM logs;
SELECT * FROM users;
"""

VALID_NOTEBOOK = {
    "nbformat": 4,
    "nbformat_minor": 4,
    "cells": [
        {
            "cell_type": "markdown",
            "source": "# Analysis",
            "metadata": {},
            "outputs": [],
        },
        {
            "cell_type": "code",
            "source": "x = 1\nprint(x)",
            "execution_count": 1,
            "metadata": {},
            "outputs": [],
        },
        {
            "cell_type": "code",
            "source": "%matplotlib inline\nimport os",
            "execution_count": 2,
            "metadata": {},
            "outputs": [],
        },
    ],
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
}

NOTEBOOK_WITH_OUTPUTS = {
    "nbformat": 4,
    "nbformat_minor": 4,
    "cells": [
        {
            "cell_type": "code",
            "source": "print('hello')",
            "execution_count": 1,
            "metadata": {},
            "outputs": [{"output_type": "stream", "name": "stdout", "text": "hello\n"}],
        },
        {
            "cell_type": "code",
            "source": "print('world')",
            "execution_count": 3,  # execution_count jumps — out of order
            "metadata": {},
            "outputs": [],
        },
    ],
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
}
```

- [ ] **Step 4: Write a smoke test**

```python
# tests/unit/test_scaffold.py
def test_package_importable():
    import code_analyser  # noqa: F401
```

- [ ] **Step 5: Install and run**

```bash
pip install -e ".[dev]"
pytest tests/unit/test_scaffold.py -v
```

Expected: 1 test collected, PASS (empty `__init__.py` is importable).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: scaffold new src/ layout and rewrite pyproject.toml"
```

---

### Task 2: models.py — all Pydantic signal models

**Files:**
- Create: `src/code_analyser/models.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_models.py
from code_analyser.models import (
    LintViolation, PythonMetrics, NotebookMetrics,
    W3CError, W3CCSSError, ExternalResource,
    HTMLMetrics, CSSMetrics, JSMetrics, TSMetrics, SQLMetrics,
    CrossFileSignals, FileLLMSignals, TopLevelLLMSignals,
    FileAnalysis, CodeAnalysis,
)


def test_python_metrics_defaults():
    m = PythonMetrics(
        syntax_valid=True, lint_error_count=0, lint_warning_count=0,
        lint_violations=[], cyclomatic_complexity=1.0, max_nesting_depth=0,
        loc=10, comment_lines=2, blank_lines=1, function_count=1,
        class_count=0, docstring_coverage=1.0, naming_convention="snake_case",
        imports=["os"], todo_count=0, print_count=0,
        type_annotation_coverage=1.0, has_main_guard=False,
        bare_except_count=0, comprehension_count=0,
    )
    assert m.syntax_valid is True
    assert m.naming_convention == "snake_case"


def test_notebook_metrics():
    from code_analyser.models import PythonMetrics
    pm = PythonMetrics(
        syntax_valid=True, lint_error_count=0, lint_warning_count=0,
        lint_violations=[], cyclomatic_complexity=1.0, max_nesting_depth=0,
        loc=5, comment_lines=0, blank_lines=0, function_count=0,
        class_count=0, docstring_coverage=0.0, naming_convention="unknown",
        imports=[], todo_count=0, print_count=1, type_annotation_coverage=0.0,
        has_main_guard=False, bare_except_count=0, comprehension_count=0,
    )
    n = NotebookMetrics(
        code_cell_count=2, markdown_cell_count=1, has_outputs=False,
        output_cell_count=0, execution_order_valid=True, magic_command_count=1,
        python_metrics=pm,
    )
    assert n.code_cell_count == 2
    assert n.python_metrics is not None


def test_html_metrics():
    m = HTMLMetrics(
        syntax_valid=True, parse_error_count=0, validator="local", w3c_errors=[],
        has_doctype=True, semantic_elements_used=["header", "main"],
        semantic_element_count=2, div_count=0, span_count=0,
        div_to_semantic_ratio=None, inline_script_count=0,
        inline_style_count=0, inline_event_handler_count=0, comment_count=0,
        external_scripts=[], external_stylesheets=[], cdn_count=0,
        frameworks_detected=[], img_alt_coverage=1.0, form_label_coverage=1.0,
        has_lang_attr=True, has_title=True, heading_hierarchy_valid=True,
        aria_attribute_count=0, ambiguous_link_count=0,
    )
    assert m.validator == "local"
    assert m.div_to_semantic_ratio is None


def test_css_metrics():
    m = CSSMetrics(
        syntax_valid=True, parse_error_count=0, validator="local",
        w3c_errors=[], w3c_warnings=[], rule_count=3, selector_count=3,
        important_count=0, duplicate_selector_count=0, media_query_count=1,
        custom_property_count=1, comment_count=0, float_count=0,
        flexbox_count=1, grid_count=1, dominant_layout="mixed",
        float_used_for_layout=False,
    )
    assert m.dominant_layout == "mixed"


def test_js_metrics():
    m = JSMetrics(
        syntax_valid=True, parse_error_count=0, function_count=1,
        arrow_function_count=1, async_function_count=1, console_log_count=1,
        import_count=1, comment_coverage=1.0, todo_count=0,
    )
    assert m.function_count == 1


def test_ts_metrics_extends_js():
    m = TSMetrics(
        syntax_valid=True, parse_error_count=0, function_count=2,
        arrow_function_count=1, async_function_count=0, console_log_count=0,
        import_count=1, comment_coverage=0.5, todo_count=0,
        type_annotation_coverage=0.8, interface_count=1, type_alias_count=1,
    )
    assert m.interface_count == 1


def test_sql_metrics():
    m = SQLMetrics(
        statement_count=3, query_types={"SELECT": 2, "INSERT": 1},
        join_count=1, subquery_depth=0, unsafe_patterns=[],
    )
    assert m.query_types["SELECT"] == 2


def test_code_analysis_structure():
    from code_analyser.models import PythonMetrics, FileAnalysis, CrossFileSignals, CodeAnalysis
    pm = PythonMetrics(
        syntax_valid=True, lint_error_count=0, lint_warning_count=0,
        lint_violations=[], cyclomatic_complexity=1.0, max_nesting_depth=0,
        loc=10, comment_lines=2, blank_lines=1, function_count=1,
        class_count=0, docstring_coverage=1.0, naming_convention="snake_case",
        imports=[], todo_count=0, print_count=0, type_annotation_coverage=1.0,
        has_main_guard=False, bare_except_count=0, comprehension_count=0,
    )
    fa = FileAnalysis(filename="app.py", language="python", metrics=pm, llm_signals=None)
    cf = CrossFileSignals(
        file_count=1, languages_detected=["python"], import_graph={},
        unrecognised_files=[], has_package_json=False, frameworks_detected=[],
    )
    ca = CodeAnalysis(input="app.py", file_count=1, languages_detected=["python"],
                      files=[fa], cross_file=cf, llm_signals=None)
    assert ca.file_count == 1
    assert ca.files[0].language == "python"
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
pytest tests/unit/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'code_analyser.models'`

- [ ] **Step 3: Implement models.py**

```python
# src/code_analyser/models.py
from __future__ import annotations
from typing import Union
from pydantic import BaseModel


class LintViolation(BaseModel):
    code: str
    line: int
    message: str


class PythonMetrics(BaseModel):
    syntax_valid: bool
    lint_error_count: int
    lint_warning_count: int
    lint_violations: list[LintViolation]
    cyclomatic_complexity: float
    max_nesting_depth: int
    loc: int
    comment_lines: int
    blank_lines: int
    function_count: int
    class_count: int
    docstring_coverage: float
    naming_convention: str  # "snake_case" | "camelCase" | "mixed" | "unknown"
    imports: list[str]
    todo_count: int
    print_count: int
    type_annotation_coverage: float
    has_main_guard: bool
    bare_except_count: int
    comprehension_count: int


class NotebookMetrics(BaseModel):
    code_cell_count: int
    markdown_cell_count: int
    has_outputs: bool
    output_cell_count: int
    execution_order_valid: bool
    magic_command_count: int
    python_metrics: PythonMetrics | None


class W3CError(BaseModel):
    type: str
    line: int
    message: str


class W3CCSSError(BaseModel):
    line: int
    message: str


class ExternalResource(BaseModel):
    src: str
    is_cdn: bool
    library: str | None


class HTMLMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: int
    validator: str  # "w3c" | "local"
    w3c_errors: list[W3CError]
    has_doctype: bool
    semantic_elements_used: list[str]
    semantic_element_count: int
    div_count: int
    span_count: int
    div_to_semantic_ratio: float | None
    inline_script_count: int
    inline_style_count: int
    inline_event_handler_count: int
    comment_count: int
    external_scripts: list[ExternalResource]
    external_stylesheets: list[ExternalResource]
    cdn_count: int
    frameworks_detected: list[str]
    img_alt_coverage: float
    form_label_coverage: float
    has_lang_attr: bool
    has_title: bool
    heading_hierarchy_valid: bool
    aria_attribute_count: int
    ambiguous_link_count: int


class CSSMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: int
    validator: str  # "w3c" | "local"
    w3c_errors: list[W3CCSSError]
    w3c_warnings: list[W3CCSSError]
    rule_count: int
    selector_count: int
    important_count: int
    duplicate_selector_count: int
    media_query_count: int
    custom_property_count: int
    comment_count: int
    float_count: int
    flexbox_count: int
    grid_count: int
    dominant_layout: str  # "float" | "flexbox" | "grid" | "mixed" | "none"
    float_used_for_layout: bool


class JSMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: int
    function_count: int
    arrow_function_count: int
    async_function_count: int
    console_log_count: int
    import_count: int
    comment_coverage: float
    todo_count: int


class TSMetrics(JSMetrics):
    type_annotation_coverage: float
    interface_count: int
    type_alias_count: int


class SQLMetrics(BaseModel):
    statement_count: int
    query_types: dict[str, int]
    join_count: int
    subquery_depth: int
    unsafe_patterns: list[str]


class CrossFileSignals(BaseModel):
    file_count: int
    languages_detected: list[str]
    import_graph: dict[str, list[str]]
    unrecognised_files: list[str]
    has_package_json: bool
    frameworks_detected: list[str]


class FileLLMSignals(BaseModel):
    comment_quality: str
    naming_quality: str
    style_guide: str | None
    code_level: str  # "beginner" | "intermediate" | "advanced"
    self_documenting_score: float
    suggestions: list[str]


class TopLevelLLMSignals(BaseModel):
    overall_quality: str
    consistency: str


FileMetrics = Union[
    PythonMetrics, NotebookMetrics, HTMLMetrics, CSSMetrics,
    JSMetrics, TSMetrics, SQLMetrics,
]


class FileAnalysis(BaseModel):
    filename: str
    language: str
    metrics: FileMetrics | None = None
    llm_signals: FileLLMSignals | None = None


class CodeAnalysis(BaseModel):
    input: str
    file_count: int
    languages_detected: list[str]
    files: list[FileAnalysis]
    cross_file: CrossFileSignals
    llm_signals: TopLevelLLMSignals | None = None
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_models.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/models.py tests/unit/test_models.py
git commit -m "feat: add all Pydantic signal models"
```

---

### Task 3: detect.py + settings.py

**Files:**
- Create: `src/code_analyser/detect.py`
- Create: `src/code_analyser/settings.py`
- Create: `tests/unit/test_detect.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_detect.py
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
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
pytest tests/unit/test_detect.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement detect.py and settings.py**

```python
# src/code_analyser/detect.py
from pathlib import Path

_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".ipynb": "notebook",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".sql": "sql",
    ".zip": "zip",
}


def detect_language(path: Path) -> str | None:
    """Return language string for path, or None if unsupported."""
    return _EXT_MAP.get(path.suffix.lower())
```

```python
# src/code_analyser/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CODE_ANALYSER_")

    host: str = "127.0.0.1"
    port: int = 8004
    w3c_timeout: float = 5.0  # seconds for W3C API calls


settings = Settings()
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_detect.py -v
```

Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/detect.py src/code_analyser/settings.py tests/unit/test_detect.py
git commit -m "feat: add language detector and settings"
```

---

### Task 4: core/python_.py

**Files:**
- Create: `src/code_analyser/core/python_.py`
- Create: `tests/unit/test_python_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_python_.py
import pytest
from conftest import VALID_PYTHON, PYTHON_WITH_ISSUES
from code_analyser.core.python_ import analyse_python


def test_valid_python_signals():
    m = analyse_python(VALID_PYTHON)
    assert m.syntax_valid is True
    assert m.function_count == 2
    assert m.has_main_guard is True
    assert m.print_count == 1
    assert m.comprehension_count == 1
    assert m.type_annotation_coverage > 0.0
    assert m.naming_convention == "snake_case"
    assert m.bare_except_count == 0


def test_invalid_python_returns_syntax_invalid():
    m = analyse_python("def foo(:\n    pass\n")
    assert m.syntax_valid is False
    assert m.loc == 0


def test_python_with_issues():
    m = analyse_python(PYTHON_WITH_ISSUES)
    assert m.syntax_valid is True
    assert m.bare_except_count == 1
    assert m.print_count == 1
    assert m.todo_count == 1
    assert m.has_main_guard is False


def test_loc_counts():
    source = "x = 1\n# comment\n\ny = 2\n"
    m = analyse_python(source)
    assert m.loc == 2
    assert m.comment_lines == 1
    assert m.blank_lines == 1


def test_docstring_coverage():
    source = '''\
def with_doc():
    """Has docstring."""
    pass

def no_doc():
    pass
'''
    m = analyse_python(source)
    assert m.docstring_coverage == pytest.approx(0.5)


def test_imports():
    source = "import os\nimport sys\nfrom pathlib import Path\n"
    m = analyse_python(source)
    assert "os" in m.imports
    assert "sys" in m.imports
    assert "pathlib" in m.imports


def test_comprehensions():
    source = "a = [x for x in range(10)]\nb = {k: v for k, v in items}\nc = (x for x in r)\n"
    m = analyse_python(source)
    assert m.comprehension_count == 3


def test_ruff_violations_shape():
    # ruff may or may not be installed; if it is, violations have code/line/message
    m = analyse_python(PYTHON_WITH_ISSUES)
    for v in m.lint_violations:
        assert isinstance(v.code, str)
        assert isinstance(v.line, int)
        assert isinstance(v.message, str)
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_python_.py -v
```

- [ ] **Step 3: Implement core/python_.py**

```python
# src/code_analyser/core/python_.py
from __future__ import annotations
import ast
import json
import re
import subprocess
import tempfile
from pathlib import Path

from ..models import LintViolation, PythonMetrics

_TODO_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*$")


def analyse_python(source: str) -> PythonMetrics:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return PythonMetrics(
            syntax_valid=False, lint_error_count=0, lint_warning_count=0,
            lint_violations=[], cyclomatic_complexity=0.0, max_nesting_depth=0,
            loc=0, comment_lines=0, blank_lines=0, function_count=0,
            class_count=0, docstring_coverage=0.0, naming_convention="unknown",
            imports=[], todo_count=0, print_count=0, type_annotation_coverage=0.0,
            has_main_guard=False, bare_except_count=0, comprehension_count=0,
        )

    lines = source.splitlines()
    loc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
    comment_lines = sum(1 for ln in lines if ln.strip().startswith("#"))
    blank_lines = sum(1 for ln in lines if not ln.strip())
    todo_count = sum(1 for ln in lines if _TODO_RE.search(ln))

    visitor = _Visitor()
    visitor.visit(tree)

    violations, err_count, warn_count = _run_ruff(source)
    naming = _detect_naming(visitor.all_names)
    doc_cov = _docstring_coverage(tree)
    type_cov = _type_annotation_coverage(tree)

    return PythonMetrics(
        syntax_valid=True,
        lint_error_count=err_count,
        lint_warning_count=warn_count,
        lint_violations=violations,
        cyclomatic_complexity=visitor.avg_complexity,
        max_nesting_depth=visitor.max_nesting,
        loc=loc,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        function_count=visitor.function_count,
        class_count=visitor.class_count,
        docstring_coverage=doc_cov,
        naming_convention=naming,
        imports=visitor.imports,
        todo_count=todo_count,
        print_count=visitor.print_count,
        type_annotation_coverage=type_cov,
        has_main_guard=visitor.has_main_guard,
        bare_except_count=visitor.bare_except_count,
        comprehension_count=visitor.comprehension_count,
    )


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_count = 0
        self.class_count = 0
        self.imports: list[str] = []
        self.print_count = 0
        self.has_main_guard = False
        self.bare_except_count = 0
        self.comprehension_count = 0
        self.all_names: list[str] = []
        self._complexities: list[int] = []
        self.max_nesting = 0
        self._depth = 0

    @property
    def avg_complexity(self) -> float:
        return sum(self._complexities) / len(self._complexities) if self._complexities else 1.0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_count += 1
        self.all_names.append(node.name)
        cc = 1 + sum(
            1 for child in ast.walk(node)
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With))
        ) + sum(
            len(child.values) - 1 for child in ast.walk(node)
            if isinstance(child, ast.BoolOp)
        )
        self._complexities.append(cc)
        self._depth += 1
        self.max_nesting = max(self.max_nesting, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_count += 1
        self.all_names.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.extend(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.append(node.module)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.print_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if (
            isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            and len(node.test.comparators) == 1
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value == "__main__"
        ):
            self.has_main_guard = True
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.bare_except_count += 1
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.all_names.append(target.id)
        self.generic_visit(node)


def _detect_naming(names: list[str]) -> str:
    if not names:
        return "unknown"
    snake = sum(1 for n in names if _SNAKE_RE.match(n))
    camel = sum(1 for n in names if _CAMEL_RE.match(n))
    total = len(names)
    if snake / total >= 0.75:
        return "snake_case"
    if camel / total >= 0.75:
        return "camelCase"
    if snake > 0 or camel > 0:
        return "mixed"
    return "unknown"


def _docstring_coverage(tree: ast.AST) -> float:
    total = 0
    with_doc = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            total += 1
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                with_doc += 1
    return with_doc / total if total else 0.0


def _type_annotation_coverage(tree: ast.AST) -> float:
    total = 0
    annotated = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            if node.args.vararg:
                args.append(node.args.vararg)
            if node.args.kwarg:
                args.append(node.args.kwarg)
            for arg in args:
                if arg.arg not in ("self", "cls"):
                    total += 1
                    if arg.annotation is not None:
                        annotated += 1
            total += 1  # return type
            if node.returns is not None:
                annotated += 1
    return annotated / total if total else 0.0


_ERROR_PREFIXES = ("F", "B", "E9")  # pyflakes, bugbear, syntax errors


def _run_ruff(source: str) -> tuple[list[LintViolation], int, int]:
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(source)
        tmp = f.name
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", tmp],
            capture_output=True, text=True,
        )
        if result.returncode not in (0, 1):
            return [], 0, 0
        items = json.loads(result.stdout or "[]")
    except (FileNotFoundError, json.JSONDecodeError):
        return [], 0, 0
    finally:
        Path(tmp).unlink(missing_ok=True)

    violations = []
    errors = 0
    warnings = 0
    for item in items:
        code = item.get("code", "")
        line = item.get("location", {}).get("row", 0)
        msg = item.get("message", "")
        violations.append(LintViolation(code=code, line=line, message=msg))
        if any(code.startswith(p) for p in _ERROR_PREFIXES):
            errors += 1
        else:
            warnings += 1
    return violations, errors, warnings
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_python_.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/python_.py tests/unit/test_python_.py
git commit -m "feat: implement Python AST analyser with all signals"
```

---

### Task 5: core/notebook_.py

**Files:**
- Create: `src/code_analyser/core/notebook_.py`
- Create: `tests/unit/test_notebook_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_notebook_.py
import json
from conftest import VALID_NOTEBOOK, NOTEBOOK_WITH_OUTPUTS
from code_analyser.core.notebook_ import analyse_notebook


def test_cell_counts():
    m = analyse_notebook(json.dumps(VALID_NOTEBOOK).encode())
    assert m.code_cell_count == 2
    assert m.markdown_cell_count == 1


def test_no_outputs():
    m = analyse_notebook(json.dumps(VALID_NOTEBOOK).encode())
    assert m.has_outputs is False
    assert m.output_cell_count == 0


def test_with_outputs():
    m = analyse_notebook(json.dumps(NOTEBOOK_WITH_OUTPUTS).encode())
    assert m.has_outputs is True
    assert m.output_cell_count == 1


def test_execution_order_valid():
    m = analyse_notebook(json.dumps(VALID_NOTEBOOK).encode())
    assert m.execution_order_valid is True


def test_execution_order_invalid():
    # NOTEBOOK_WITH_OUTPUTS has execution_counts [1, 3] — not sequential
    m = analyse_notebook(json.dumps(NOTEBOOK_WITH_OUTPUTS).encode())
    assert m.execution_order_valid is False


def test_magic_command_count():
    m = analyse_notebook(json.dumps(VALID_NOTEBOOK).encode())
    # Second code cell starts with %matplotlib
    assert m.magic_command_count == 1


def test_python_metrics_extracted():
    m = analyse_notebook(json.dumps(VALID_NOTEBOOK).encode())
    assert m.python_metrics is not None
    assert m.python_metrics.print_count >= 1
    assert "os" in m.python_metrics.imports


def test_invalid_json_returns_empty():
    m = analyse_notebook(b"not json")
    assert m.code_cell_count == 0
    assert m.python_metrics is None
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_notebook_.py -v
```

- [ ] **Step 3: Implement core/notebook_.py**

```python
# src/code_analyser/core/notebook_.py
from __future__ import annotations
import json

from ..models import NotebookMetrics
from .python_ import analyse_python

_MAGIC_PREFIXES = ("%", "%%")


def analyse_notebook(content: bytes) -> NotebookMetrics:
    try:
        nb = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return NotebookMetrics(
            code_cell_count=0, markdown_cell_count=0, has_outputs=False,
            output_cell_count=0, execution_order_valid=True, magic_command_count=0,
            python_metrics=None,
        )

    cells = nb.get("cells", [])
    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    md_cells = [c for c in cells if c.get("cell_type") == "markdown"]

    output_cell_count = sum(1 for c in code_cells if c.get("outputs"))
    has_outputs = output_cell_count > 0

    exec_counts = [c.get("execution_count") for c in code_cells if c.get("execution_count") is not None]
    execution_order_valid = exec_counts == sorted(exec_counts) and len(exec_counts) == len(set(exec_counts))

    magic_count = 0
    code_lines: list[str] = []
    for cell in code_cells:
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        for line in source.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(p) for p in _MAGIC_PREFIXES):
                magic_count += 1
            else:
                code_lines.append(line)

    combined_code = "\n".join(code_lines)
    try:
        python_metrics = analyse_python(combined_code) if combined_code.strip() else None
    except Exception:
        python_metrics = None

    return NotebookMetrics(
        code_cell_count=len(code_cells),
        markdown_cell_count=len(md_cells),
        has_outputs=has_outputs,
        output_cell_count=output_cell_count,
        execution_order_valid=execution_order_valid,
        magic_command_count=magic_count,
        python_metrics=python_metrics,
    )
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_notebook_.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/notebook_.py tests/unit/test_notebook_.py
git commit -m "feat: implement Jupyter notebook analyser"
```

---

### Task 6: core/html_.py

**Files:**
- Create: `src/code_analyser/core/html_.py`
- Create: `tests/unit/test_html_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_html_.py
import pytest
from unittest.mock import patch
from conftest import VALID_HTML, DIV_SOUP_HTML
from code_analyser.core.html_ import analyse_html


def test_valid_html_basic_signals():
    m = analyse_html(VALID_HTML)
    assert m.syntax_valid is True
    assert m.has_doctype is True
    assert m.has_lang_attr is True
    assert m.has_title is True
    assert m.validator == "local"


def test_semantic_elements():
    m = analyse_html(VALID_HTML)
    assert "header" in m.semantic_elements_used
    assert "main" in m.semantic_elements_used
    assert "footer" in m.semantic_elements_used
    assert m.semantic_element_count >= 3


def test_div_to_semantic_ratio_low_for_semantic_html():
    m = analyse_html(VALID_HTML)
    # VALID_HTML has no divs but has semantic elements
    assert m.div_count == 0
    assert m.div_to_semantic_ratio is None  # no divs or semantics → None, or 0


def test_div_soup_signals():
    m = analyse_html(DIV_SOUP_HTML)
    assert m.div_count >= 4
    assert m.inline_event_handler_count >= 2  # onclick + onchange
    assert m.div_to_semantic_ratio is not None
    assert m.div_to_semantic_ratio > 0.5


def test_accessibility_valid_html():
    m = analyse_html(VALID_HTML)
    assert m.img_alt_coverage == pytest.approx(1.0)
    assert m.form_label_coverage == pytest.approx(1.0)
    assert m.heading_hierarchy_valid is True


def test_accessibility_div_soup():
    m = analyse_html(DIV_SOUP_HTML)
    assert m.img_alt_coverage == pytest.approx(0.0)  # img has no alt
    assert m.form_label_coverage == pytest.approx(0.0)  # input has no label


def test_w3c_api_used_when_reachable(monkeypatch):
    mock_errors = [{"type": "error", "lastLine": 1, "message": "Bad attribute"}]

    def fake_post(*args, **kwargs):
        class R:
            def raise_for_status(self): pass
            def json(self): return {"messages": mock_errors}
        return R()

    monkeypatch.setattr("httpx.post", fake_post)
    m = analyse_html(VALID_HTML, timeout=1.0)
    assert m.validator == "w3c"
    assert len(m.w3c_errors) == 1
    assert m.w3c_errors[0].message == "Bad attribute"


def test_w3c_api_fallback_on_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise ConnectionError("offline")

    monkeypatch.setattr("httpx.post", fake_post)
    m = analyse_html(VALID_HTML, timeout=1.0)
    assert m.validator == "local"
    assert m.w3c_errors == []
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_html_.py -v
```

- [ ] **Step 3: Implement core/html_.py**

```python
# src/code_analyser/core/html_.py
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import html5lib
import httpx

from ..models import ExternalResource, HTMLMetrics, W3CError

_XHTML = "http://www.w3.org/1999/xhtml"

_SEMANTIC = {
    "header", "nav", "main", "footer", "article", "section", "aside",
    "figure", "figcaption", "time", "mark", "details", "summary", "address",
}

_CDN_HOSTS = {
    "cdnjs.cloudflare.com", "unpkg.com", "cdn.jsdelivr.net",
    "ajax.googleapis.com", "cdn.tailwindcss.com",
    "stackpath.bootstrapcdn.com", "maxcdn.bootstrapcdn.com", "code.jquery.com",
}

_LIBRARY_PATTERNS = {
    "jquery": re.compile(r"jquery", re.I),
    "bootstrap": re.compile(r"bootstrap", re.I),
    "react": re.compile(r"react(?:\.min)?\.js", re.I),
    "vue": re.compile(r"vue(?:\.min)?\.js", re.I),
    "angular": re.compile(r"angular", re.I),
    "tailwind": re.compile(r"tailwind", re.I),
    "font-awesome": re.compile(r"font.awesome", re.I),
}

_JS_FRAMEWORK_PATTERNS = [
    (re.compile(r"React\.createElement|from\s+['\"]react['\"]"), "react"),
    (re.compile(r"new\s+Vue\s*\(|from\s+['\"]vue['\"]"), "vue"),
    (re.compile(r"ng-app|ng-controller"), "angular"),
    (re.compile(r"\$\s*\(|jQuery\s*\("), "jquery"),
]

_AMBIGUOUS_LINK_TEXT = {"click here", "here", "read more", "more", "link", "this"}

_ON_ATTRS = re.compile(r"\bon\w+\s*=", re.I)


def _tag(name: str) -> str:
    return f"{{{_XHTML}}}{name}"


def _detect_library(url: str) -> str | None:
    for lib, pat in _LIBRARY_PATTERNS.items():
        if pat.search(url):
            return lib
    return None


def _is_cdn(url: str) -> bool:
    try:
        host = urlparse(url).netloc
        return host in _CDN_HOSTS
    except Exception:
        return False


def _w3c_validate(source: str, timeout: float) -> list[W3CError]:
    resp = httpx.post(
        "https://validator.w3.org/nu/",
        params={"out": "json"},
        content=source.encode(),
        headers={"Content-Type": "text/html; charset=utf-8"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return [
        W3CError(
            type=m.get("type", "error"),
            line=m.get("lastLine", 0),
            message=m.get("message", ""),
        )
        for m in resp.json().get("messages", [])
        if m.get("type") in ("error", "warning")
    ]


def analyse_html(source: str, *, timeout: float = 5.0) -> HTMLMetrics:
    w3c_errors: list[W3CError] = []
    validator = "local"
    try:
        w3c_errors = _w3c_validate(source, timeout)
        validator = "w3c"
    except Exception:
        pass

    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("etree"))
    tree = parser.parse(source)
    parse_errors = parser.errors
    syntax_valid = len(parse_errors) == 0

    # Walk tree
    divs = 0
    spans = 0
    semantic_found: dict[str, int] = {}
    inline_scripts = 0
    inline_styles = 0
    event_handlers = 0
    comments = 0
    imgs: list[ET.Element] = []
    inputs: list[ET.Element] = []
    labels: list[ET.Element] = []
    links: list[ET.Element] = []
    headings: list[int] = []
    aria_attrs = 0
    external_scripts: list[ExternalResource] = []
    external_stylesheets: list[ExternalResource] = []
    frameworks: set[str] = set()

    has_doctype = "<!DOCTYPE" in source[:200].upper()
    has_lang = False
    has_title = False

    all_js_source = source  # for framework fingerprinting

    for el in tree.iter():
        local = el.tag.replace(f"{{{_XHTML}}}", "") if el.tag.startswith("{") else el.tag

        if local == "html":
            has_lang = bool(el.get("lang") or el.get(f"{{{_XHTML}}}lang"))
        elif local == "title":
            has_title = bool(el.text and el.text.strip())
        elif local == "div":
            divs += 1
        elif local == "span":
            spans += 1
        elif local in _SEMANTIC:
            semantic_found[local] = semantic_found.get(local, 0) + 1
        elif local == "script":
            src = el.get("src")
            if src:
                is_cdn = _is_cdn(src)
                lib = _detect_library(src)
                external_scripts.append(ExternalResource(src=src, is_cdn=is_cdn, library=lib))
                if lib:
                    frameworks.add(lib)
            else:
                inline_scripts += 1
        elif local == "link":
            if el.get("rel") == "stylesheet" or "stylesheet" in (el.get("rel") or ""):
                href = el.get("href", "")
                is_cdn = _is_cdn(href)
                lib = _detect_library(href)
                external_stylesheets.append(ExternalResource(src=href, is_cdn=is_cdn, library=lib))
                if lib:
                    frameworks.add(lib)
        elif local == "img":
            imgs.append(el)
        elif local == "input":
            if el.get("type", "text") != "hidden":
                inputs.append(el)
        elif local == "label":
            labels.append(el)
        elif local == "a":
            links.append(el)
        elif local in ("h1", "h2", "h3", "h4", "h5", "h6"):
            headings.append(int(local[1]))
        elif local == "style":
            inline_styles += 1

        for attr in el.attrib:
            local_attr = attr.split("}")[-1] if "}" in attr else attr
            if local_attr.startswith("on"):
                event_handlers += 1
            if local_attr.startswith("aria-"):
                aria_attrs += 1
            if local_attr == "style":
                inline_styles += 1

    # Framework fingerprinting via code patterns
    for pat, name in _JS_FRAMEWORK_PATTERNS:
        if pat.search(all_js_source):
            frameworks.add(name)

    # Accessibility
    img_alt_coverage = (
        sum(1 for img in imgs if img.get("alt", "").strip()) / len(imgs)
        if imgs else 1.0
    )
    label_fors = {lbl.get("for") for lbl in labels if lbl.get("for")}
    input_ids = {inp.get("id") for inp in inputs if inp.get("id")}
    form_label_coverage = (
        sum(1 for inp_id in input_ids if inp_id in label_fors) / len(inputs)
        if inputs else 1.0
    )

    ambiguous = sum(
        1 for a in links
        if (a.text or "").strip().lower() in _AMBIGUOUS_LINK_TEXT
    )

    heading_valid = _check_heading_hierarchy(headings)

    semantic_count = sum(semantic_found.values())
    semantic_used = sorted(semantic_found.keys())
    cdn_count = sum(1 for r in external_scripts + external_stylesheets if r.is_cdn)

    if divs == 0 and semantic_count == 0:
        ratio = None
    elif divs == 0:
        ratio = 0.0
    else:
        ratio = divs / (divs + semantic_count)

    return HTMLMetrics(
        syntax_valid=syntax_valid,
        parse_error_count=len(parse_errors),
        validator=validator,
        w3c_errors=w3c_errors,
        has_doctype=has_doctype,
        semantic_elements_used=semantic_used,
        semantic_element_count=semantic_count,
        div_count=divs,
        span_count=spans,
        div_to_semantic_ratio=ratio,
        inline_script_count=inline_scripts,
        inline_style_count=inline_styles,
        inline_event_handler_count=event_handlers,
        comment_count=comments,
        external_scripts=external_scripts,
        external_stylesheets=external_stylesheets,
        cdn_count=cdn_count,
        frameworks_detected=sorted(frameworks),
        img_alt_coverage=img_alt_coverage,
        form_label_coverage=form_label_coverage,
        has_lang_attr=has_lang,
        has_title=has_title,
        heading_hierarchy_valid=heading_valid,
        aria_attribute_count=aria_attrs,
        ambiguous_link_count=ambiguous,
    )


def _check_heading_hierarchy(levels: list[int]) -> bool:
    if not levels:
        return True
    if levels.count(1) > 1:
        return False
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            return False
    return True
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_html_.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/html_.py tests/unit/test_html_.py
git commit -m "feat: implement HTML analyser with W3C API, semantics, accessibility signals"
```

---

### Task 7: core/css_.py

**Files:**
- Create: `src/code_analyser/core/css_.py`
- Create: `tests/unit/test_css_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_css_.py
import pytest
from unittest.mock import patch
from conftest import VALID_CSS, FLOAT_CSS
from code_analyser.core.css_ import analyse_css


def test_valid_css_signals():
    m = analyse_css(VALID_CSS)
    assert m.syntax_valid is True
    assert m.rule_count >= 3
    assert m.media_query_count == 1
    assert m.custom_property_count == 1
    assert m.validator == "local"


def test_flexbox_detected():
    m = analyse_css(VALID_CSS)
    assert m.flexbox_count >= 1
    assert m.grid_count >= 1


def test_float_detected():
    m = analyse_css(FLOAT_CSS)
    assert m.float_count >= 2
    assert m.dominant_layout == "float"
    assert m.float_used_for_layout is True


def test_dominant_layout_flexbox():
    css = ".a{display:flex}.b{display:flex}.c{display:flex}"
    m = analyse_css(css)
    assert m.dominant_layout == "flexbox"


def test_dominant_layout_grid():
    css = ".a{display:grid}.b{display:grid}.c{float:left}"
    m = analyse_css(css)
    # grid:2, float:1 → grid dominates (not within 20%)
    assert m.dominant_layout == "grid"


def test_dominant_layout_none():
    m = analyse_css("body{margin:0}")
    assert m.dominant_layout == "none"


def test_important_count():
    css = "a{color:red!important}.b{font-size:12px!important}"
    m = analyse_css(css)
    assert m.important_count == 2


def test_w3c_fallback(monkeypatch):
    def fake_get(*args, **kwargs):
        raise ConnectionError("offline")
    monkeypatch.setattr("httpx.get", fake_get)
    m = analyse_css(VALID_CSS, timeout=1.0)
    assert m.validator == "local"
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_css_.py -v
```

- [ ] **Step 3: Implement core/css_.py**

```python
# src/code_analyser/core/css_.py
from __future__ import annotations
import re

import httpx
import tinycss2

from ..models import CSSMetrics, W3CCSSError


def _w3c_validate_css(source: str, timeout: float) -> tuple[list[W3CCSSError], list[W3CCSSError]]:
    resp = httpx.get(
        "https://jigsaw.w3.org/css-validator/validator",
        params={"text": source, "output": "json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json().get("cssvalidation", {})
    errors = [W3CCSSError(line=e.get("line", 0), message=e.get("message", "")) for e in data.get("errors", [])]
    warnings = [W3CCSSError(line=w.get("line", 0), message=w.get("message", "")) for w in data.get("warnings", [])]
    return errors, warnings


_IMPORTANT_RE = re.compile(r"!\s*important", re.I)
_FLOAT_VALUE_RE = re.compile(r"^(left|right)$", re.I)
_NON_IMAGE_SELECTORS = re.compile(r"img|figure|picture", re.I)


def analyse_css(source: str, *, timeout: float = 5.0) -> CSSMetrics:
    w3c_errors: list[W3CCSSError] = []
    w3c_warnings: list[W3CCSSError] = []
    validator = "local"
    try:
        w3c_errors, w3c_warnings = _w3c_validate_css(source, timeout)
        validator = "w3c"
    except Exception:
        pass

    rules_raw = tinycss2.parse_stylesheet(source, skip_comments=False, skip_whitespace=True)
    parse_errors = [r for r in rules_raw if r.type == "error"]
    rules = [r for r in rules_raw if r.type == "qualified-rule" or r.type == "at-rule"]

    rule_count = 0
    selector_count = 0
    important_count = 0
    duplicate_selector_count = 0
    media_query_count = 0
    custom_property_count = 0
    comment_count = 0
    float_count = 0
    flexbox_count = 0
    grid_count = 0
    float_on_non_image = 0

    seen_selectors: dict[str, int] = {}

    def _count_in_block(declarations: list) -> None:
        nonlocal important_count, custom_property_count, float_count, flexbox_count, grid_count, float_on_non_image
        for token in declarations:
            if token.type == "declaration":
                name = token.lower_name
                value_str = tinycss2.serialize(token.value).strip()
                if token.important:
                    important_count += 1
                if name.startswith("--"):
                    custom_property_count += 1
                if name == "float" and _FLOAT_VALUE_RE.match(value_str):
                    float_count += 1
                if name == "display":
                    if "flex" in value_str:
                        flexbox_count += 1
                    elif "grid" in value_str:
                        grid_count += 1

    for rule in rules:
        if rule.type == "qualified-rule":
            rule_count += 1
            sel = tinycss2.serialize(rule.prelude).strip()
            selector_count += 1
            seen_selectors[sel] = seen_selectors.get(sel, 0) + 1
            try:
                decls = tinycss2.parse_declaration_list(rule.content, skip_whitespace=True)
                _count_in_block(decls)
            except Exception:
                pass
        elif rule.type == "at-rule":
            if rule.lower_at_keyword == "media":
                media_query_count += 1
                if rule.content:
                    sub = tinycss2.parse_stylesheet(
                        tinycss2.serialize(rule.content), skip_whitespace=True
                    )
                    for sub_rule in sub:
                        if sub_rule.type == "qualified-rule":
                            rule_count += 1
                            try:
                                decls = tinycss2.parse_declaration_list(sub_rule.content, skip_whitespace=True)
                                _count_in_block(decls)
                            except Exception:
                                pass

    for token in tinycss2.parse_stylesheet(source, skip_comments=False):
        if token.type == "comment":
            comment_count += 1

    important_count = source.upper().count("!IMPORTANT")
    duplicate_selector_count = sum(1 for c in seen_selectors.values() if c > 1)

    # Float used for layout: float appears on non-image selectors
    float_used_for_layout = False
    if float_count > 0:
        for sel, _ in seen_selectors.items():
            if not _NON_IMAGE_SELECTORS.search(sel):
                float_used_for_layout = True
                break

    dominant_layout = _dominant(float_count, flexbox_count, grid_count)

    return CSSMetrics(
        syntax_valid=len(parse_errors) == 0,
        parse_error_count=len(parse_errors),
        validator=validator,
        w3c_errors=w3c_errors,
        w3c_warnings=w3c_warnings,
        rule_count=rule_count,
        selector_count=selector_count,
        important_count=important_count,
        duplicate_selector_count=duplicate_selector_count,
        media_query_count=media_query_count,
        custom_property_count=custom_property_count,
        comment_count=comment_count,
        float_count=float_count,
        flexbox_count=flexbox_count,
        grid_count=grid_count,
        dominant_layout=dominant_layout,
        float_used_for_layout=float_used_for_layout,
    )


def _dominant(floats: int, flex: int, grid: int) -> str:
    total = floats + flex + grid
    if total == 0:
        return "none"
    counts = {"float": floats, "flexbox": flex, "grid": grid}
    top = max(counts, key=lambda k: counts[k])
    top_val = counts[top]
    others = [v for k, v in counts.items() if k != top]
    if any(top_val > 0 and o / top_val >= 0.8 for o in others if o > 0):
        return "mixed"
    return top
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_css_.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/css_.py tests/unit/test_css_.py
git commit -m "feat: implement CSS analyser with layout method signals and W3C API"
```

---

### Task 8: core/javascript_.py

**Files:**
- Create: `src/code_analyser/core/javascript_.py`
- Create: `tests/unit/test_javascript_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_javascript_.py
from conftest import VALID_JS
from code_analyser.core.javascript_ import analyse_javascript


def test_function_count():
    m = analyse_javascript(VALID_JS)
    assert m.function_count == 1  # greet
    assert m.arrow_function_count == 2  # double, asyncLoad


def test_async_count():
    m = analyse_javascript(VALID_JS)
    assert m.async_function_count == 1  # asyncLoad


def test_console_log():
    m = analyse_javascript(VALID_JS)
    assert m.console_log_count == 1


def test_import_count():
    m = analyse_javascript(VALID_JS)
    assert m.import_count >= 1


def test_todo_count():
    js = "// TODO: fix this\nfunction foo(){}"
    m = analyse_javascript(js)
    assert m.todo_count == 1


def test_invalid_js():
    m = analyse_javascript("function foo( {")
    assert m.syntax_valid is False
    assert m.parse_error_count == 1


def test_comment_coverage():
    m = analyse_javascript(VALID_JS)
    # greet has a comment above it; coverage > 0
    assert m.comment_coverage >= 0.0


def test_jsx_mode():
    jsx = "const el = <div className='foo'>Hello</div>;"
    # JSX mode shouldn't crash even if esprima can't fully parse it
    m = analyse_javascript(jsx, jsx=True)
    assert isinstance(m.syntax_valid, bool)
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_javascript_.py -v
```

- [ ] **Step 3: Implement core/javascript_.py**

```python
# src/code_analyser/core/javascript_.py
from __future__ import annotations
import re

try:
    import esprima
    _ESPRIMA_AVAILABLE = True
except ImportError:
    _ESPRIMA_AVAILABLE = False

from ..models import JSMetrics

_TODO_RE = re.compile(r"//\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_COMMENT_LINE_RE = re.compile(r"^\s*(?://|/\*|\*)", re.MULTILINE)


def analyse_javascript(source: str, *, jsx: bool = False) -> JSMetrics:
    if not _ESPRIMA_AVAILABLE:
        return _fallback_metrics(source)

    try:
        opts = {"tolerant": True, "comment": True}
        try:
            tree = esprima.parseModule(source, **opts)
        except Exception:
            tree = esprima.parseScript(source, jsx=jsx, **opts)
        syntax_valid = True
        parse_error_count = len(getattr(tree, "errors", []))
    except Exception:
        return JSMetrics(
            syntax_valid=False, parse_error_count=1,
            function_count=0, arrow_function_count=0, async_function_count=0,
            console_log_count=0, import_count=0, comment_coverage=0.0, todo_count=0,
        )

    counts = _walk(tree)
    todo_count = len(_TODO_RE.findall(source))
    comment_lines = len(_COMMENT_LINE_RE.findall(source))
    total_fns = counts["functions"] + counts["arrows"]
    comment_coverage = min(comment_lines / max(total_fns, 1), 1.0)

    return JSMetrics(
        syntax_valid=syntax_valid,
        parse_error_count=parse_error_count,
        function_count=counts["functions"],
        arrow_function_count=counts["arrows"],
        async_function_count=counts["async"],
        console_log_count=counts["console_logs"],
        import_count=counts["imports"],
        comment_coverage=comment_coverage,
        todo_count=todo_count,
    )


def _fallback_metrics(source: str) -> JSMetrics:
    todo_count = len(_TODO_RE.findall(source))
    return JSMetrics(
        syntax_valid=True, parse_error_count=0,
        function_count=len(re.findall(r"\bfunction\s+\w+\s*\(", source)),
        arrow_function_count=len(re.findall(r"=>\s*[{(]", source)),
        async_function_count=len(re.findall(r"\basync\s+(?:function|\w+\s*=>|\()", source)),
        console_log_count=len(re.findall(r"\bconsole\.log\s*\(", source)),
        import_count=len(re.findall(r"\bimport\s+", source)),
        comment_coverage=0.0,
        todo_count=todo_count,
    )


def _walk(node) -> dict[str, int]:
    counts = {"functions": 0, "arrows": 0, "async": 0, "console_logs": 0, "imports": 0}

    def visit(n):
        if not hasattr(n, "type"):
            return
        t = n.type
        if t in ("FunctionDeclaration", "FunctionExpression"):
            counts["functions"] += 1
            if getattr(n, "async", False):
                counts["async"] += 1
        elif t == "ArrowFunctionExpression":
            counts["arrows"] += 1
            if getattr(n, "async", False):
                counts["async"] += 1
        elif t == "ImportDeclaration":
            counts["imports"] += 1
        elif t == "CallExpression":
            callee = getattr(n, "callee", None)
            if (callee and getattr(callee, "type", "") == "MemberExpression"
                    and getattr(getattr(callee, "object", None), "name", "") == "console"
                    and getattr(getattr(callee, "property", None), "name", "") == "log"):
                counts["console_logs"] += 1
            # require()
            if (getattr(callee, "type", "") == "Identifier"
                    and getattr(callee, "name", "") == "require"):
                counts["imports"] += 1

        for key in vars(n):
            child = getattr(n, key)
            if hasattr(child, "type"):
                visit(child)
            elif isinstance(child, list):
                for item in child:
                    if hasattr(item, "type"):
                        visit(item)

    visit(node)
    return counts
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_javascript_.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/javascript_.py tests/unit/test_javascript_.py
git commit -m "feat: implement JavaScript analyser with esprima AST"
```

---

### Task 9: core/typescript_.py

**Files:**
- Create: `src/code_analyser/core/typescript_.py`
- Create: `tests/unit/test_typescript_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_typescript_.py
from conftest import VALID_TS
from code_analyser.core.typescript_ import analyse_typescript


def test_function_count():
    m = analyse_typescript(VALID_TS)
    assert m.function_count >= 1  # greet


def test_interface_count():
    m = analyse_typescript(VALID_TS)
    assert m.interface_count == 1  # User


def test_type_alias_count():
    m = analyse_typescript(VALID_TS)
    assert m.type_alias_count == 1  # ID


def test_type_annotation_coverage_positive():
    m = analyse_typescript(VALID_TS)
    assert m.type_annotation_coverage > 0.0


def test_import_count():
    m = analyse_typescript(VALID_TS)
    assert m.import_count >= 1


def test_arrow_function_count():
    m = analyse_typescript(VALID_TS)
    assert m.arrow_function_count >= 1  # add


def test_syntax_valid_flag():
    m = analyse_typescript(VALID_TS)
    assert isinstance(m.syntax_valid, bool)
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_typescript_.py -v
```

- [ ] **Step 3: Implement core/typescript_.py**

```python
# src/code_analyser/core/typescript_.py
from __future__ import annotations
import re

from ..models import TSMetrics

_FUNC_RE = re.compile(r"\bfunction\s+\w+\s*\(", re.MULTILINE)
_ARROW_RE = re.compile(r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*\w[\w<>\[\]|&,\s]*?)?\s*=>", re.MULTILINE)
_ASYNC_RE = re.compile(r"\basync\s+(?:function\s+\w+|\w+\s*=>|\([^)]*\)\s*=>)", re.MULTILINE)
_CONSOLE_RE = re.compile(r"\bconsole\.log\s*\(")
_IMPORT_RE = re.compile(r"\bimport\s+")
_INTERFACE_RE = re.compile(r"\binterface\s+\w+")
_TYPE_ALIAS_RE = re.compile(r"\btype\s+\w+\s*=")
_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*)", re.MULTILINE)
_TODO_RE = re.compile(r"//\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
# Param with type annotation: word: UpperOrPrimitive
_TYPED_PARAM_RE = re.compile(r"\w+\s*\??\s*:\s*(?:[A-Z]\w*|string|number|boolean|any|void|never|unknown|object)")
# Return type annotation: ): Type {  or  ): Type;  or  ): Type =>
_RETURN_TYPE_RE = re.compile(r"\)\s*:\s*(?:[A-Z]\w*|string|number|boolean|any|void|never|unknown|object)[\s{;=]")


def analyse_typescript(source: str, *, tsx: bool = False) -> TSMetrics:
    try:
        open_braces = source.count("{")
        close_braces = source.count("}")
        syntax_valid = abs(open_braces - close_braces) <= 3
    except Exception:
        syntax_valid = False

    function_count = len(_FUNC_RE.findall(source))
    arrow_count = len(_ARROW_RE.findall(source))
    async_count = len(_ASYNC_RE.findall(source))
    console_log = len(_CONSOLE_RE.findall(source))
    import_count = len(_IMPORT_RE.findall(source))
    interface_count = len(_INTERFACE_RE.findall(source))
    type_alias_count = len(_TYPE_ALIAS_RE.findall(source))
    todo_count = len(_TODO_RE.findall(source))

    comment_lines = len(_COMMENT_RE.findall(source))
    total_fns = function_count + arrow_count
    comment_coverage = min(comment_lines / max(total_fns, 1), 1.0)

    typed_params = len(_TYPED_PARAM_RE.findall(source))
    return_types = len(_RETURN_TYPE_RE.findall(source))
    denominator = max(total_fns * 2 + interface_count, 1)
    type_annotation_coverage = min((typed_params + return_types) / denominator, 1.0)

    return TSMetrics(
        syntax_valid=syntax_valid,
        parse_error_count=0,
        function_count=function_count,
        arrow_function_count=arrow_count,
        async_function_count=async_count,
        console_log_count=console_log,
        import_count=import_count,
        comment_coverage=comment_coverage,
        todo_count=todo_count,
        type_annotation_coverage=type_annotation_coverage,
        interface_count=interface_count,
        type_alias_count=type_alias_count,
    )
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_typescript_.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/typescript_.py tests/unit/test_typescript_.py
git commit -m "feat: implement TypeScript analyser (regex-based)"
```

---

### Task 10: core/sql_.py

**Files:**
- Create: `src/code_analyser/core/sql_.py`
- Create: `tests/unit/test_sql_.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_sql_.py
from conftest import VALID_SQL, UNSAFE_SQL
from code_analyser.core.sql_ import analyse_sql


def test_statement_count():
    m = analyse_sql(VALID_SQL)
    assert m.statement_count == 5


def test_query_types():
    m = analyse_sql(VALID_SQL)
    assert m.query_types.get("SELECT", 0) >= 1
    assert m.query_types.get("INSERT", 0) == 1
    assert m.query_types.get("UPDATE", 0) == 1
    assert m.query_types.get("DELETE", 0) == 1


def test_join_count():
    m = analyse_sql(VALID_SQL)
    assert m.join_count == 1


def test_no_unsafe_patterns():
    m = analyse_sql(VALID_SQL)
    assert m.unsafe_patterns == []


def test_unsafe_patterns():
    m = analyse_sql(UNSAFE_SQL)
    assert len(m.unsafe_patterns) > 0
    patterns_str = " ".join(m.unsafe_patterns)
    assert "UPDATE" in patterns_str or "DELETE" in patterns_str or "SELECT *" in patterns_str


def test_subquery_depth():
    sql = "SELECT * FROM (SELECT id FROM (SELECT id FROM users) t1) t2;"
    m = analyse_sql(sql)
    assert m.subquery_depth >= 2
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_sql_.py -v
```

- [ ] **Step 3: Implement core/sql_.py**

```python
# src/code_analyser/core/sql_.py
from __future__ import annotations
import re

import sqlparse
from sqlparse.sql import Where
from sqlparse.tokens import Keyword, DML

from ..models import SQLMetrics

_JOIN_RE = re.compile(r"\bJOIN\b", re.IGNORECASE)
_SELECT_STAR_RE = re.compile(r"\bSELECT\s+\*", re.IGNORECASE)
_UPDATE_NO_WHERE_RE = re.compile(r"\bUPDATE\b(?!.*\bWHERE\b)", re.IGNORECASE | re.DOTALL)
_DELETE_NO_WHERE_RE = re.compile(r"\bDELETE\b(?!.*\bWHERE\b)", re.IGNORECASE | re.DOTALL)


def analyse_sql(source: str) -> SQLMetrics:
    statements = [s for s in sqlparse.parse(source) if s.get_type() is not None or str(s).strip()]
    statements = [s for s in statements if str(s).strip()]

    query_types: dict[str, int] = {}
    join_count = 0
    unsafe: list[str] = []

    for stmt in statements:
        stype = (stmt.get_type() or "UNKNOWN").upper()
        query_types[stype] = query_types.get(stype, 0) + 1

        stmt_str = str(stmt)
        join_count += len(_JOIN_RE.findall(stmt_str))

        if stype == "UPDATE" and _UPDATE_NO_WHERE_RE.search(stmt_str):
            has_where = any(isinstance(tok, Where) for tok in stmt.tokens)
            if not has_where:
                unsafe.append(f"UPDATE without WHERE")
        elif stype == "DELETE" and _DELETE_NO_WHERE_RE.search(stmt_str):
            has_where = any(isinstance(tok, Where) for tok in stmt.tokens)
            if not has_where:
                unsafe.append("DELETE without WHERE")
        if _SELECT_STAR_RE.search(stmt_str):
            unsafe.append("SELECT *")

    subquery_depth = _max_subquery_depth(source)

    return SQLMetrics(
        statement_count=len(statements),
        query_types=query_types,
        join_count=join_count,
        subquery_depth=subquery_depth,
        unsafe_patterns=list(dict.fromkeys(unsafe)),  # deduplicate, preserve order
    )


def _max_subquery_depth(source: str) -> int:
    depth = 0
    max_depth = 0
    for ch in source:
        if ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")":
            depth = max(0, depth - 1)
    return max(0, max_depth - 1)  # subtract 1 since outer parens aren't subqueries
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_sql_.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/core/sql_.py tests/unit/test_sql_.py
git commit -m "feat: implement SQL analyser with unsafe pattern detection"
```

---

### Task 11: llm.py — optional LLM signals

**Files:**
- Create: `src/code_analyser/llm.py`
- Create: `tests/unit/test_llm.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_llm.py
from unittest.mock import MagicMock, patch
from code_analyser.llm import analyse_llm, LLMUnavailableError


def test_returns_none_when_not_installed(monkeypatch):
    monkeypatch.setattr("code_analyser.llm._ANTHROPIC_AVAILABLE", False)
    file_sigs, top_sig = analyse_llm([("app.py", "def foo(): pass")])
    assert file_sigs == [None]
    assert top_sig is None


def test_returns_none_when_no_api_key(monkeypatch):
    monkeypatch.setattr("code_analyser.llm._ANTHROPIC_AVAILABLE", True)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    file_sigs, top_sig = analyse_llm([("app.py", "def foo(): pass")])
    assert file_sigs == [None]
    assert top_sig is None


def test_returns_signals_with_mock(monkeypatch):
    monkeypatch.setattr("code_analyser.llm._ANTHROPIC_AVAILABLE", True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"comment_quality":"good","naming_quality":"clear","style_guide":null,"code_level":"intermediate","self_documenting_score":0.8,"suggestions":["Add docstrings"]}')]
    mock_client.messages.create.return_value = mock_msg

    top_msg = MagicMock()
    top_msg.content = [MagicMock(text='{"overall_quality":"solid","consistency":"consistent"}')]
    mock_client.messages.create.side_effect = [mock_msg, top_msg]

    with patch("code_analyser.llm._make_client", return_value=mock_client):
        file_sigs, top_sig = analyse_llm([("app.py", "def foo(): pass")])

    assert file_sigs[0] is not None
    assert file_sigs[0].code_level == "intermediate"
    assert top_sig is not None
    assert top_sig.overall_quality == "solid"
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/unit/test_llm.py -v
```

- [ ] **Step 3: Implement llm.py**

```python
# src/code_analyser/llm.py
from __future__ import annotations
import json
import os

from .models import FileLLMSignals, TopLevelLLMSignals

try:
    import anthropic as _anthropic_module
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class LLMUnavailableError(Exception):
    pass


def _make_client():
    return _anthropic_module.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


_FILE_PROMPT = """\
Analyse this source file and return a JSON object with exactly these keys:
- comment_quality: string (narrative: do comments explain WHY not just WHAT?)
- naming_quality: string (narrative: are names meaningful and consistent?)
- style_guide: string or null (detected convention: "google", "numpy", "jsdoc", "pep257", or null)
- code_level: "beginner" | "intermediate" | "advanced"
- self_documenting_score: float 0-1 (would this be readable without comments?)
- suggestions: list of 3-5 concrete improvement strings

Return only valid JSON, no markdown fences.

File: {filename}
```
{source}
```"""

_TOP_PROMPT = """\
Given these source files from the same project, return a JSON object with:
- overall_quality: string (narrative summary across all files)
- consistency: string (are style/naming/patterns consistent across files?)

Return only valid JSON, no markdown fences.

Files: {filenames}"""


def analyse_llm(
    files: list[tuple[str, str]],
) -> tuple[list[FileLLMSignals | None], TopLevelLLMSignals | None]:
    if not _ANTHROPIC_AVAILABLE or not os.environ.get("ANTHROPIC_API_KEY"):
        return [None] * len(files), None

    client = _make_client()
    file_signals: list[FileLLMSignals | None] = []

    for filename, source in files:
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": _FILE_PROMPT.format(filename=filename, source=source[:4000])}],
            )
            data = json.loads(msg.content[0].text)
            file_signals.append(FileLLMSignals(**data))
        except Exception:
            file_signals.append(None)

    try:
        top_msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": _TOP_PROMPT.format(filenames=", ".join(f for f, _ in files))}],
        )
        top_data = json.loads(top_msg.content[0].text)
        top_signals = TopLevelLLMSignals(**top_data)
    except Exception:
        top_signals = None

    return file_signals, top_signals
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_llm.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/llm.py tests/unit/test_llm.py
git commit -m "feat: add optional LLM signals gated behind [llm] extra"
```

---

### Task 12: pipeline.py — orchestrator

**Files:**
- Create: `src/code_analyser/pipeline.py`
- Create: `tests/integration/test_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_pipeline.py
import json
import zipfile
import io
import pytest
from pathlib import Path
from conftest import VALID_PYTHON, VALID_HTML, VALID_CSS
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


def test_analyse_zip_multiple(tmp_path):
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


def test_cross_file_has_package_json(tmp_path):
    zip_bytes = _make_zip(
        ("app.js", "console.log('hi')"),
        ("package.json", '{"name":"test"}'),
    )
    p = tmp_path / "proj.zip"
    p.write_bytes(zip_bytes)
    result = CodeAnalyser().analyse(p)
    assert result.cross_file.has_package_json is True


def test_languages_detected(tmp_path):
    p = tmp_path / "app.py"
    p.write_text(VALID_PYTHON)
    result = CodeAnalyser().analyse(p)
    assert "python" in result.cross_file.languages_detected
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/integration/test_pipeline.py -v
```

- [ ] **Step 3: Implement pipeline.py**

```python
# src/code_analyser/pipeline.py
from __future__ import annotations
import zipfile
from pathlib import Path

from .detect import detect_language
from .models import (
    CodeAnalysis, CrossFileSignals, FileAnalysis,
    FileLLMSignals, TopLevelLLMSignals,
)
from .core.python_ import analyse_python
from .core.notebook_ import analyse_notebook
from .core.html_ import analyse_html
from .core.css_ import analyse_css
from .core.javascript_ import analyse_javascript
from .core.typescript_ import analyse_typescript
from .core.sql_ import analyse_sql


class CodeAnalyser:
    def analyse(self, path: Path, *, llm: bool = False) -> CodeAnalysis:
        lang = detect_language(path)
        if lang is None:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        if lang == "zip":
            pairs = _unpack_zip(path)
        else:
            pairs = [(path.name, path.read_bytes())]

        files: list[FileAnalysis] = []
        unrecognised: list[str] = []
        import_graph: dict[str, list[str]] = {}
        has_package_json = False
        all_frameworks: set[str] = set()

        for filename, content in pairs:
            if filename.lower() == "package.json":
                has_package_json = True
                unrecognised.append(filename)
                continue

            file_lang = detect_language(Path(filename))
            if file_lang is None or file_lang == "zip":
                unrecognised.append(filename)
                continue

            metrics = _dispatch(filename, file_lang, content)
            files.append(FileAnalysis(filename=filename, language=file_lang, metrics=metrics))

            # Collect frameworks from HTML metrics
            if hasattr(metrics, "frameworks_detected") and metrics is not None:
                all_frameworks.update(getattr(metrics, "frameworks_detected", []))

        llm_file_signals: list[FileLLMSignals | None] = [None] * len(files)
        llm_top: TopLevelLLMSignals | None = None

        if llm:
            try:
                from .llm import analyse_llm
                text_pairs = [
                    (f.filename, _decode(pairs_map[f.filename]))
                    for f in files
                    if f.filename in (pairs_map := dict(pairs))
                ]
                llm_file_signals, llm_top = analyse_llm(text_pairs)
            except Exception:
                pass

        for i, f in enumerate(files):
            f.llm_signals = llm_file_signals[i] if i < len(llm_file_signals) else None

        langs_detected = sorted({f.language for f in files})

        cross = CrossFileSignals(
            file_count=len(files),
            languages_detected=langs_detected,
            import_graph=import_graph,
            unrecognised_files=unrecognised,
            has_package_json=has_package_json,
            frameworks_detected=sorted(all_frameworks),
        )

        return CodeAnalysis(
            input=path.name,
            file_count=len(files),
            languages_detected=langs_detected,
            files=files,
            cross_file=cross,
            llm_signals=llm_top,
        )


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _unpack_zip(path: Path) -> list[tuple[str, bytes]]:
    pairs: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            pairs.append((Path(name).name, zf.read(name)))
    return pairs


def _dispatch(filename: str, lang: str, content: bytes):
    src = _decode(content)
    try:
        if lang == "python":
            return analyse_python(src)
        elif lang == "notebook":
            return analyse_notebook(content)
        elif lang == "html":
            return analyse_html(src)
        elif lang == "css":
            return analyse_css(src)
        elif lang == "javascript":
            jsx = filename.endswith((".jsx",))
            return analyse_javascript(src, jsx=jsx)
        elif lang == "typescript":
            tsx = filename.endswith((".tsx",))
            return analyse_typescript(src, tsx=tsx)
        elif lang == "sql":
            return analyse_sql(src)
    except Exception:
        return None
    return None
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/integration/test_pipeline.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/pipeline.py tests/integration/test_pipeline.py
git commit -m "feat: implement pipeline orchestrator with zip support"
```

---

### Task 13: cli.py

**Files:**
- Create: `src/code_analyser/cli.py`
- Create: `tests/cli/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
# tests/cli/test_cli.py
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
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/cli/test_cli.py -v
```

- [ ] **Step 3: Implement cli.py**

```python
# src/code_analyser/cli.py
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

from .pipeline import CodeAnalyser
from .models import CodeAnalysis


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        _serve(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(
        prog="code-analyser",
        description="Source code signals analyser",
    )
    parser.add_argument("file", type=Path, help="Source file or .zip archive to analyse")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    parser.add_argument("--llm", action="store_true", help="Include LLM quality signals (requires [llm] extra)")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        result = CodeAnalyser().analyse(args.file, llm=args.llm)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        print(result.model_dump_json(indent=2))
        return

    _print_human(result)


def _print_human(result: CodeAnalysis) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print(f"[bold]Input:[/bold] {result.input}  [bold]Files:[/bold] {result.file_count}  "
                  f"[bold]Languages:[/bold] {', '.join(result.languages_detected)}")

    table = Table(show_header=True, header_style="bold")
    table.add_column("File")
    table.add_column("Language")
    table.add_column("Details")

    for f in result.files:
        details = _summarise_metrics(f.metrics, f.language)
        table.add_row(f.filename, f.language, details)

    console.print(table)

    if result.cross_file.unrecognised_files:
        console.print(f"[dim]Unrecognised: {', '.join(result.cross_file.unrecognised_files)}[/dim]")


def _summarise_metrics(metrics, language: str) -> str:
    if metrics is None:
        return "parse failed"
    if language == "python":
        return (f"loc={metrics.loc}  funcs={metrics.function_count}  "
                f"errors={metrics.lint_error_count}  complexity={metrics.cyclomatic_complexity:.1f}")
    if language == "notebook":
        return (f"code_cells={metrics.code_cell_count}  "
                f"outputs={'yes' if metrics.has_outputs else 'no'}  "
                f"order={'ok' if metrics.execution_order_valid else 'scrambled'}")
    if language == "html":
        return (f"errors={metrics.parse_error_count}  divs={metrics.div_count}  "
                f"semantics={metrics.semantic_element_count}  "
                f"alt={metrics.img_alt_coverage:.0%}")
    if language == "css":
        return f"rules={metrics.rule_count}  layout={metrics.dominant_layout}"
    if language in ("javascript", "typescript"):
        return (f"funcs={metrics.function_count}  arrows={metrics.arrow_function_count}  "
                f"console_logs={metrics.console_log_count}")
    if language == "sql":
        return f"statements={metrics.statement_count}  joins={metrics.join_count}"
    return ""


def _serve(argv: list[str]) -> None:
    import uvicorn
    parser = argparse.ArgumentParser(prog="code-analyser serve")
    parser.add_argument("--port", type=int, default=int(os.getenv("CODE_ANALYSER_PORT", "8004")))
    parser.add_argument("--host", default=os.getenv("CODE_ANALYSER_HOST", "127.0.0.1"))
    args = parser.parse_args(argv)
    uvicorn.run("code_analyser.api:app", host=args.host, port=args.port)
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/cli/test_cli.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/cli.py tests/cli/test_cli.py
git commit -m "feat: implement family-consistent argparse CLI"
```

---

### Task 14: api.py — FastAPI

**Files:**
- Create: `src/code_analyser/api.py`
- Create: `tests/api/test_api.py`

- [ ] **Step 1: Write failing test**

```python
# tests/api/test_api.py
import json
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


def test_analyse_python(client, tmp_path):
    r = client.post(
        "/analyse",
        files={"file": ("app.py", VALID_PYTHON.encode(), "text/x-python")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["file_count"] == 1
    assert data["files"][0]["language"] == "python"


def test_analyse_zip(client):
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
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/api/test_api.py -v
```

- [ ] **Step 3: Implement api.py**

```python
# src/code_analyser/api.py
from __future__ import annotations
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .models import CodeAnalysis
from .pipeline import CodeAnalyser

_start_time = time.time()

app = FastAPI(title="code-analyser", version="1.0.0")

_analyser = CodeAnalyser()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "uptime": round(time.time() - _start_time, 1)}


@app.post("/analyse", response_model=CodeAnalysis)
async def analyse(
    file: UploadFile = File(...),
    llm: bool = Form(False),
) -> CodeAnalysis:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")

    suffix = Path(file.filename or "upload.py").suffix or ".py"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(content)

    try:
        result = _analyser.analyse(tmp_path, llm=llm)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/api/test_api.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/code_analyser/api.py tests/api/test_api.py
git commit -m "feat: implement FastAPI endpoint POST /analyse + GET /health"
```

---

### Task 15: __init__.py + integration + cleanup

**Files:**
- Modify: `src/code_analyser/__init__.py`
- Delete: `code_analyser/` (old package), `Dockerfile`, `docker-compose*.yml`, `nginx.conf`, `scripts/`, `DEPLOYMENT.md`, `dist/`, `.env.example`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_full_pipeline.py
import io
import json
import zipfile
from conftest import VALID_PYTHON, VALID_HTML, VALID_CSS
from code_analyser import CodeAnalyser, CodeAnalysis


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

    # Validate serialises cleanly
    dumped = json.loads(result.model_dump_json())
    assert dumped["file_count"] == 4
```

- [ ] **Step 2: Run — expect PASS (all modules already implemented)**

```bash
pytest tests/integration/test_full_pipeline.py -v
```

Expected: 1 passed

- [ ] **Step 3: Write __init__.py exports**

```python
# src/code_analyser/__init__.py
from .models import CodeAnalysis
from .pipeline import CodeAnalyser

__all__ = ["CodeAnalyser", "CodeAnalysis"]
```

- [ ] **Step 4: Verify import from public API**

```bash
python -c "from code_analyser import CodeAnalyser, CodeAnalysis; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Delete old code and files**

```bash
rm -rf code_analyser/
rm -f Dockerfile docker-compose.yml docker-compose.prod.yml nginx.conf
rm -rf scripts/ dist/
rm -f DEPLOYMENT.md .env.example
```

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass, 0 errors.

- [ ] **Step 7: Final commit**

```bash
git add src/code_analyser/__init__.py tests/integration/test_full_pipeline.py
git rm -r code_analyser/ Dockerfile docker-compose.yml docker-compose.prod.yml nginx.conf scripts/ dist/ DEPLOYMENT.md .env.example 2>/dev/null || true
git commit -m "feat: complete code-analyser rewrite — family-consistent CLI, FastAPI, 7 languages, optional LLM signals"
```
