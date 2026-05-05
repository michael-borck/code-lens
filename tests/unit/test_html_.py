import httpx
import pytest
from conftest import VALID_HTML, DIV_SOUP_HTML
from code_analyser.core.html_ import analyse_html


def _no_network(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("httpx.post", _raise)


def test_valid_html_basic_signals(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_html(VALID_HTML)
    assert m.syntax_valid is True
    assert m.has_doctype is True
    assert m.has_lang_attr is True
    assert m.has_title is True
    assert m.validator == "local"


def test_semantic_elements(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_html(VALID_HTML)
    assert "header" in m.semantic_elements_used
    assert "main" in m.semantic_elements_used
    assert "footer" in m.semantic_elements_used
    assert m.semantic_element_count >= 3


def test_div_to_semantic_ratio_low_for_semantic_html(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_html(VALID_HTML)
    assert m.div_count == 0
    assert m.div_to_semantic_ratio == pytest.approx(0.0)


def test_div_soup_signals(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_html(DIV_SOUP_HTML)
    assert m.div_count >= 4
    assert m.inline_event_handler_count >= 2
    assert m.div_to_semantic_ratio is not None
    assert m.div_to_semantic_ratio > 0.5


def test_accessibility_valid_html(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_html(VALID_HTML)
    assert m.img_alt_coverage == pytest.approx(1.0)
    assert m.form_label_coverage == pytest.approx(1.0)
    assert m.heading_hierarchy_valid is True


def test_accessibility_div_soup(monkeypatch):
    _no_network(monkeypatch)
    m = analyse_html(DIV_SOUP_HTML)
    assert m.img_alt_coverage == pytest.approx(0.0)
    assert m.form_label_coverage == pytest.approx(0.0)


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
    def _raise(*a, **kw):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("httpx.post", _raise)
    m = analyse_html(VALID_HTML, timeout=1.0)
    assert m.validator == "local"
    assert m.w3c_errors == []
