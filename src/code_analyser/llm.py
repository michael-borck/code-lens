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
