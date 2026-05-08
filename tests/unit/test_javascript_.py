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
    assert m.import_count == 1  # the single `import { helper } from './utils.js';`


def test_todo_count():
    js = "// TODO: fix this\nfunction foo(){}"
    m = analyse_javascript(js)
    assert m.todo_count == 1


def test_invalid_js():
    m = analyse_javascript("function foo( {")
    assert m.syntax_valid is False
    assert m.parse_error_count == 1


def test_comment_coverage():
    # VALID_JS has 1 function (greet) + 2 arrows (double, asyncLoad) = 3 callable units.
    # Exactly 1 line matches the comment-line regex (`// say hello`), so
    # coverage = 1/3 ≈ 0.333. Anchor against the actual ratio rather than `>= 0.0`.
    m = analyse_javascript(VALID_JS)
    assert 0.30 < m.comment_coverage < 0.40


def test_jsx_parsing_when_enabled():
    """JSX expressions parse cleanly when jsx=True."""
    src = "const App = () => <div>hello</div>;"
    result = analyse_javascript(src, jsx=True)
    assert result.syntax_valid is True
    assert result.parse_error_count == 0
    assert result.arrow_function_count == 1


def test_jsx_fails_without_flag():
    """JSX without jsx=True fails to parse (proves the flag actually does something)."""
    src = "const App = () => <div>hello</div>;"
    result = analyse_javascript(src, jsx=False)
    assert result.syntax_valid is False
