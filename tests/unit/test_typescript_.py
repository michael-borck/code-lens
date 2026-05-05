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
