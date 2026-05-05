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
