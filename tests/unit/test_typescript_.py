from conftest import VALID_TS
from code_analyser.core.typescript_ import analyse_typescript


def test_function_count():
    m = analyse_typescript(VALID_TS)
    assert m.function_count == 1  # greet


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
    assert m.import_count == 1


def test_arrow_function_count():
    m = analyse_typescript(VALID_TS)
    assert m.arrow_function_count == 1  # add


def test_typescript_unmatched_braces():
    """Brace-balance heuristic flags clearly unbalanced braces as not-balanced."""
    # typescript_.analyse_typescript: syntax_valid = abs(open - close) <= 3.
    # Source below has 5 `{` and 0 `}`, so the diff is 5 → syntax_valid is False.
    result = analyse_typescript(
        "function foo() { if (a) { if (b) { if (c) { if (d) { return 42"
    )
    assert result.syntax_valid is False


def test_brace_heuristic_misses_real_syntax_errors():
    """The brace heuristic is NOT a real TS parser.

    This source is syntactically invalid TypeScript (missing `)` after `(x`)
    but the open and close braces are balanced, so the heuristic reports
    `syntax_valid=True`. This test pins the documented limitation: brace
    balance is not parsing. Its existence is the contract — when (if) we
    ever add a real parser via the [parser] extra, this test will need
    to be updated, and that's the signal.
    """
    src = "function foo() { if (x { return; } }"
    # Sanity: braces ARE balanced (3 open, 3 close).
    assert src.count("{") == src.count("}")
    result = analyse_typescript(src)
    assert result.syntax_valid is True
