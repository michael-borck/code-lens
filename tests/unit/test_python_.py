# tests/unit/test_python_.py
import shutil

import pytest
from conftest import VALID_PYTHON, PYTHON_WITH_ISSUES
from code_analyser.core.python_ import analyse_python


@pytest.mark.slow
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


@pytest.mark.slow
def test_ruff_violations_shape():
    """ruff is invoked as a subprocess in python_._run_ruff; skip when the
    binary is not on PATH. PYTHON_WITH_ISSUES has bare except / unused
    imports / etc., so when ruff IS available we expect at least one
    violation — without that assertion the for-loop is vacuous.
    """
    if shutil.which("ruff") is None:
        pytest.skip("ruff binary not on PATH; cannot exercise lint subprocess")
    m = analyse_python(PYTHON_WITH_ISSUES)
    assert len(m.lint_violations) > 0
    for v in m.lint_violations:
        assert isinstance(v.code, str)
        assert isinstance(v.line, int)
        assert isinstance(v.message, str)


def test_main_guard_not_triggered_by_nested_if():
    source = '''\
def foo():
    if __name__ == "__main__":
        pass
'''
    m = analyse_python(source)
    assert m.has_main_guard is False
