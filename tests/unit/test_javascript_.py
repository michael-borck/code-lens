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
    assert m.comment_coverage >= 0.0


def test_jsx_mode():
    jsx = "const el = <div className='foo'>Hello</div>;"
    m = analyse_javascript(jsx, jsx=True)
    assert isinstance(m.syntax_valid, bool)
