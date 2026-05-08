import httpx
from conftest import VALID_CSS, FLOAT_CSS
from code_analyser.core.css_ import analyse_css


def _no_network(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("httpx.get", _raise)


def test_valid_css_signals(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_css(VALID_CSS)
    assert m.syntax_valid is True
    assert m.rule_count >= 3
    assert m.media_query_count == 1
    assert m.custom_property_count == 1
    assert m.validator == "local"


def test_flexbox_detected(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_css(VALID_CSS)
    assert m.flexbox_count >= 1
    assert m.grid_count >= 1


def test_float_detected(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_css(FLOAT_CSS)
    assert m.float_count >= 2
    assert m.dominant_layout == "float"
    assert m.float_used_for_layout is True


def test_dominant_layout_flexbox(monkeypatch):
    _no_network(monkeypatch)
    css = ".a{display:flex}.b{display:flex}.c{display:flex}"
    m = analyse_css(css)
    assert m.dominant_layout == "flexbox"


def test_dominant_layout_grid(monkeypatch):
    _no_network(monkeypatch)
    css = ".a{display:grid}.b{display:grid}.c{float:left}"
    m = analyse_css(css)
    assert m.dominant_layout == "grid"


def test_dominant_layout_none(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_css("body{margin:0}")
    assert m.dominant_layout == "none"


def test_important_count(monkeypatch):
    _no_network(monkeypatch)
    css = "a{color:red!important}.b{font-size:12px!important}"
    m = analyse_css(css)
    assert m.important_count == 2
