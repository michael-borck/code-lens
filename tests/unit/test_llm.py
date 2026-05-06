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

    top_msg = MagicMock()
    top_msg.content = [MagicMock(text='{"overall_quality":"solid","consistency":"consistent"}')]
    mock_client.messages.create.side_effect = [mock_msg, top_msg]

    with patch("code_analyser.llm._make_client", return_value=mock_client):
        file_sigs, top_sig = analyse_llm([("app.py", "def foo(): pass")])

    assert file_sigs[0] is not None
    assert file_sigs[0].code_level == "intermediate"
    assert top_sig is not None
    assert top_sig.overall_quality == "solid"
