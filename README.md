# code-analyser

Analyses source code files and returns style violations, complexity metrics, and quality indicators. Designed as a low-level tool — feed it a file, get back structured JSON.

Part of the [analyser family](#the-analyser-family).

> **Status**: Early development. Currently supports Python via ruff and basic AST metrics. Multi-language support and alignment with the family API pattern is in progress.

## Install

```bash
pip install code-analyser
```

Requires Python 3.11+.

## Usage

### Python

```python
from codelens import analyse

result = analyse("submission.py")

print(f"Lines:      {result['metrics']['lines_of_code']}")
print(f"Complexity: {result['metrics']['cyclomatic_complexity']}")
print(f"Issues:     {len(result['issues'])}")
```

### HTTP API

```bash
# Start the server
uvicorn codelens.main:app --port 8004

curl -X POST http://localhost:8004/api/v1/analyze/python \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello():\n    print(\"Hello\")", "language": "python"}'
```

## Supported languages

| Language | Status |
|---|---|
| Python | supported (ruff, AST metrics) |
| JavaScript, Java, others | planned |

## Output

```json
{
  "language": "python",
  "metrics": {
    "lines_of_code": 42,
    "cyclomatic_complexity": 3,
    "maintainability_index": 74.2
  },
  "issues": [
    {"rule": "E501", "line": 12, "message": "line too long (92 > 88 characters)"}
  ],
  "summary": {
    "error_count": 0,
    "warning_count": 1,
    "style_count": 2
  }
}
```

## The analyser family

Low-level analysis tools. Each accepts files directly and returns structured JSON. Build your own UI or pipeline on top.

| Package | Handles |
|---|---|
| [speech-analyser](https://github.com/michael-borck/speech-analyser) | audio and video files — transcript and speech metrics |
| [video-analyser](https://github.com/michael-borck/video-analyser) | video files — frames, scenes, and visual quality |
| [document-analyser](https://github.com/michael-borck/document-analyser) | PDF, DOCX, PPTX, TXT — text and readability |
| [code-analyser](https://github.com/michael-borck/code-analyser) | source code — style, complexity, and quality metrics |
| [records-analyser](https://github.com/michael-borck/records-analyser) | CSV, Excel, SQLite, Parquet, JSON — data profiling |
| [multi-analyser](https://github.com/michael-borck/multi-analyser) | any file — detects format and routes to the right tool |

## License

MIT
