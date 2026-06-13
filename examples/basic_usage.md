# code-analyser — basic usage

Analyse a source file (`.py`, `.js`, `.ts`, `.html`, `.css`, `.sql`, `.ipynb`, or a `.zip` of them) for structural code signals.

## Install

```bash
pip install code-analyser
```

## CLI

```bash
# Human-readable table
code-analyser app.py

# JSON output
code-analyser app.py --json

# Include LLM quality signals (requires the [llm] extra)
code-analyser app.py --llm
```

## Python

```python
from code_analyser import CodeAnalyser

result = CodeAnalyser().analyse("app.py")
print(result.languages_detected, result.file_count)
for f in result.files:
    print(f.filename, f.language, f.metrics)
```

## HTTP

```bash
# Start the server (default port 8004)
code-analyser serve

# Analyse a source file via multipart upload
curl -F file=@app.py http://localhost:8004/analyse
```
