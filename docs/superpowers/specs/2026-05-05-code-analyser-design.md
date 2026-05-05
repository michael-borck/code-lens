# code-analyser Design

## Goal

Rewrite code-analyser to align with the analyser family pattern: argparse CLI (`code-analyser file.py --json`), FastAPI `/analyse` endpoint, signals-only output (no rubrics, grading, or DB), multi-language support via internal per-language dispatching.

## Scope

**Two tools from this design session:**
- `code-analyser` (port 8004) — source files and archives, all supported languages
- `wordpress-analyser` (port 8005) — WordPress themes/plugins (separate tool, separate design)

**Also noted (separate future designs):**
- `folder-analyser` (port 8006) — meta-analyser: walks a directory, dispatches file types to family members, adds structural signals
- `git-analyser` (port 8007) — meta-analyser: walks git history, dispatches file content to code-analyser, adds history signals

### Supported languages (core, v1)

| Language | Parser / Tool |
|---|---|
| Python | `ast` (stdlib) + `ruff` (subprocess) |
| HTML | `html5lib` |
| CSS | `tinycss2` |
| JavaScript / JSX | `esprima` (pure-Python port, JSX mode for `.jsx`) |
| TypeScript / TSX | `esprima` + type annotation heuristics (JSX mode for `.tsx`) |
| SQL | `sqlparse` |

### Input

- Single source file (any supported extension)
- Zip archive — each file dispatched by detected language, results aggregated

### Optional extras

- `[llm]` — LLM-assisted quality signals via Anthropic SDK. Requires `ANTHROPIC_API_KEY`. Silently unavailable if not installed.

### Out of scope

- Rubric evaluation, grading, scoring — consumer responsibility
- JWT auth, SQLite DB, Docker sandbox — all from old code-lens, dropped entirely
- WordPress-specific signals — wordpress-analyser (separate tool)
- NLP engine — future shared library; comment text analysis lives in `[llm]` for now
- folder-analyser, git-analyser — separate tools
- Dynamic accessibility (colour contrast, focus order, screen reader behaviour) — requires a running browser and a URL; use Lighthouse or axe-core at the consumer layer

## Architecture

```
code_analyser/
  cli.py            # argparse: code-analyser file.py [--json] [--llm]
  api.py            # FastAPI: POST /analyse, GET /health
  settings.py       # pydantic-settings, CODE_ANALYSER_ prefix
  models.py         # CodeAnalysis + per-language signal models
  detect.py         # language detection: extension + content sniffing
  pipeline.py       # orchestrate: unpack → detect → dispatch → aggregate
  core/
    python_.py      # ast + ruff subprocess
    html_.py        # html5lib + accessibility heuristics
    css_.py         # tinycss2 + metrics
    javascript_.py  # esprima + metrics
    typescript_.py  # extends javascript_, adds type annotation coverage
    sql_.py         # sqlparse + safety pattern checks
  llm.py            # [llm] extra — LLM quality signals (gated)
```

## Data Flow

```
Input (file or zip)
  └─→ Unpacker         → list of (filename, content) pairs
  └─→ LanguageDetector → language per file (extension + shebang sniff)
  └─→ Dispatcher       → routes each file to the right core/ module
        ├─→ PythonAnalyser   → PythonMetrics | None
        ├─→ HTMLAnalyser     → HTMLMetrics | None
        ├─→ CSSAnalyser      → CSSMetrics | None
        ├─→ JSAnalyser       → JSMetrics | None
        ├─→ TSAnalyser       → TSMetrics | None
        └─→ SQLAnalyser      → SQLMetrics | None
  └─→ CrossFileAggregator → import graph, unrecognised file list
  └─→ LLMAnalyser?     → LLMSignals | None  (if --llm + [llm] installed)
  └─→ CodeAnalysis      (final output)
```

Each stage is wrapped in try/except. A parse failure sets `syntax_valid: false` and returns what metrics are recoverable. A complete stage failure returns `null` for that file's metrics.

## Signal Set

### Python (`core/python_.py`)

- `syntax_valid: bool`
- `lint_error_count: int`, `lint_warning_count: int`
- `lint_violations: list[{code, line, message}]`
- `cyclomatic_complexity: float` (average across functions)
- `max_nesting_depth: int`
- `loc: int`, `comment_lines: int`, `blank_lines: int`
- `function_count: int`, `class_count: int`
- `docstring_coverage: float` (0–1, % of defs with a docstring)
- `naming_convention: str` ("snake_case" | "camelCase" | "mixed" | "unknown")
- `imports: list[str]`
- `todo_count: int` (TODO / FIXME / HACK / XXX in comments)

### HTML (`core/html_.py`)

Validation: calls the **Nu HTML Checker API** (`validator.w3.org/nu/`) with the raw HTML bytes, parses the JSON response. Falls back to `html5lib` local parsing if the API is unreachable (timeout or offline). The `validator` field in output indicates which was used: `"w3c"` or `"local"`.

- `syntax_valid: bool`, `parse_error_count: int`
- `validator: str` — `"w3c"` | `"local"` (which validation source was used)
- `w3c_errors: list[{type, line, message}]` — from Nu HTML Checker (empty if local fallback)
- `has_doctype: bool`

**HTML5 semantic structure:**
- `semantic_elements_used: list[str]` — which semantic tags appear (header, nav, main, footer, article, section, aside, figure, figcaption, time, mark, details, summary, address)
- `semantic_element_count: int` — total count of semantic element instances
- `div_count: int` — total `<div>` elements
- `span_count: int` — total `<span>` elements
- `div_to_semantic_ratio: float` — `div_count / (div_count + semantic_element_count)`, 0–1. High values (>0.8) indicate "div soup". `null` if no divs or semantic elements present.

- `inline_script_count: int` — `<script>` blocks without a `src` attribute
- `inline_style_count: int` — `style="..."` attributes + `<style>` blocks
- `inline_event_handler_count: int` — `onclick="..."`, `onchange="..."`, `onsubmit="..."` etc. (separation-of-concerns violation)
- `comment_count: int`

**External resources and framework detection:**
- `external_scripts: list[{src, is_cdn, library}]` — all `<script src="...">` tags. `is_cdn: true` if src matches known CDN hostnames. `library` is the detected library name if recognisable (e.g. `"jquery"`, `"bootstrap"`, `"react"`, `"vue"`, `"tailwind"`, `"font-awesome"`) or `null`.
- `external_stylesheets: list[{href, is_cdn, library}]` — all `<link rel="stylesheet" href="...">` tags, same CDN/library detection.
- `cdn_count: int` — total CDN-hosted resources (scripts + stylesheets combined).
- `frameworks_detected: list[str]` — libraries/frameworks fingerprinted across HTML + JS files via code-level patterns (not just CDN links): `"react"` (React.createElement, from 'react'), `"vue"` (new Vue(), from 'vue'), `"angular"` (ng-app, ng-controller), `"jquery"` ($(), jQuery), `"bootstrap"`, `"tailwind"`, `"svelte"`, `"bulma"`, `"materialize"`.

CDN hostnames detected: `cdnjs.cloudflare.com`, `unpkg.com`, `cdn.jsdelivr.net`, `ajax.googleapis.com`, `cdn.tailwindcss.com`, `stackpath.bootstrapcdn.com`, `maxcdn.bootstrapcdn.com`, `code.jquery.com`. New patterns added without schema changes.

**Static accessibility signals** (file-based, no browser needed):
- `img_alt_coverage: float` (0–1, % of `<img>` with non-empty alt)
- `form_label_coverage: float` (0–1, % of inputs with an associated `<label>`)
- `has_lang_attr: bool` (`<html lang="...">` present)
- `has_title: bool` (`<title>` element present and non-empty)
- `heading_hierarchy_valid: bool` (no skipped levels, e.g. h1→h3; no multiple h1s)
- `aria_attribute_count: int` (total ARIA attributes used)
- `ambiguous_link_count: int` (links whose text is "click here", "here", "read more", etc.)

**Out of scope (dynamic, needs browser + URL):** colour contrast ratios, focus order, screen reader compatibility, interactive element behaviour — use Lighthouse or axe-core at the consumer layer.

### CSS (`core/css_.py`)

Validation: calls the **W3C CSS Validator API** (`jigsaw.w3.org/css-validator/`) with the raw CSS. Falls back to `tinycss2` local parsing if the API is unreachable. The `validator` field indicates which was used.

- `syntax_valid: bool`, `parse_error_count: int`
- `validator: str` — `"w3c"` | `"local"`
- `w3c_errors: list[{line, message}]`, `w3c_warnings: list[{line, message}]`
- `rule_count: int`, `selector_count: int`
- `important_count: int`
- `duplicate_selector_count: int`
- `media_query_count: int`
- `custom_property_count: int` (CSS variables)
- `comment_count: int`

**Layout method signals:**
- `float_count: int` — number of `float: left/right` declarations
- `flexbox_count: int` — number of `display: flex` / `display: inline-flex` declarations
- `grid_count: int` — number of `display: grid` / `display: inline-grid` declarations
- `dominant_layout: str` — `"float"` | `"flexbox"` | `"grid"` | `"mixed"` | `"none"` (whichever has the highest count; `"mixed"` if two or more are within 20% of each other)
- `float_used_for_layout: bool` — heuristic: float used on non-image elements (suggests old-school layout pattern rather than just wrapping text around an image)

### JavaScript (`core/javascript_.py`)

- `syntax_valid: bool`, `parse_error_count: int`
- `function_count: int` (regular + arrow, reported separately)
- `arrow_function_count: int`
- `async_function_count: int`
- `console_log_count: int`
- `import_count: int` (ES module imports + require() calls)
- `comment_coverage: float` (0–1, % of functions with a preceding comment)
- `todo_count: int`

### TypeScript (`core/typescript_.py`)

All JavaScript signals, plus:
- `type_annotation_coverage: float` (0–1, heuristic: % of function params/returns with type annotations)
- `interface_count: int`, `type_alias_count: int`

### SQL (`core/sql_.py`)

- `statement_count: int`
- `query_types: dict[str, int]` (SELECT/INSERT/UPDATE/DELETE/CREATE/etc.)
- `join_count: int`
- `subquery_depth: int` (max nesting)
- `unsafe_patterns: list[str]` (UPDATE without WHERE, DELETE without WHERE, SELECT *)

### Cross-file (`pipeline.py`)

Always present — for single-file input, `import_graph` and `unrecognised_files` are empty.

- `file_count: int`
- `languages_detected: list[str]`
- `import_graph: dict[str, list[str]]` (filename → files it imports, best-effort)
- `unrecognised_files: list[str]`
- `has_package_json: bool` — signals use of a Node.js build toolchain
- `frameworks_detected: list[str]` — aggregated across all files (HTML CDN links + JS code-level patterns)

### LLM signals (`llm.py`, `[llm]` extra)

Appears at file level and at top level (cross-file narrative). Both `null` if `--llm` not passed.

Per file:
- `comment_quality: str` — narrative: do comments explain WHY not just WHAT?
- `naming_quality: str` — narrative: are names meaningful and consistent?
- `style_guide: str | null` — detected convention ("google", "numpy", "jsdoc", "pep257", etc.)
- `code_level: str` — "beginner" | "intermediate" | "advanced"
- `self_documenting_score: float` — 0–1, would this be readable without comments?
- `suggestions: list[str]` — top 3–5 concrete improvements

Top level (cross-file):
- `overall_quality: str` — narrative summary across all files
- `consistency: str` — are style/naming/patterns consistent across files?

## Output Schema

```json
{
  "input": "submission.zip",
  "file_count": 3,
  "languages_detected": ["python", "html", "css"],
  "files": [
    {
      "filename": "app.py",
      "language": "python",
      "metrics": {
        "syntax_valid": true,
        "lint_error_count": 3,
        "lint_warning_count": 7,
        "lint_violations": [
          {"code": "E501", "line": 12, "message": "line too long"}
        ],
        "cyclomatic_complexity": 4.2,
        "max_nesting_depth": 3,
        "loc": 120,
        "comment_lines": 18,
        "blank_lines": 14,
        "function_count": 8,
        "class_count": 2,
        "docstring_coverage": 0.75,
        "naming_convention": "snake_case",
        "imports": ["os", "pathlib", "fastapi"],
        "todo_count": 2
      },
      "llm_signals": null
    }
  ],
  "cross_file": {
    "import_graph": {"app.py": ["utils.py"]},
    "unrecognised_files": ["README.md"]
  },
  "llm_signals": null
}
```

## CLI Interface

```
code-analyser file.py                    # human-readable summary
code-analyser file.py --json             # machine-readable JSON
code-analyser submission.zip --json      # archive input
code-analyser file.py --json --llm       # include LLM signals
code-analyser serve                      # start API server on port 8004
code-analyser serve --port 9000          # custom port
```

## HTTP API

```
POST /analyse
Content-Type: multipart/form-data
  file    (required) single source file or .zip
  llm     (optional, bool, default false)

Response: 200 CodeAnalysis JSON
          422 unsupported file type or empty file
          500 pipeline error

GET /health
Response: {"status": "ok", "uptime": 12.3}
```

## Error Handling

| Situation | API | CLI |
|---|---|---|
| Unsupported file type | 422 + supported extensions listed | non-zero exit + message |
| Unsupported file inside zip | noted in `unrecognised_files` | same |
| Parse failure for a file | `syntax_valid: false`, metrics still attempted | same |
| Complete stage failure | `metrics: null` for that file, others continue | same |
| `--llm` without `[llm]` installed | 422 + install hint | non-zero + message |
| `--llm` without `ANTHROPIC_API_KEY` | 422 + env var hint | non-zero + message |
| W3C API unreachable / timeout | falls back to local parser, `validator: "local"` in output | same |

## Dependencies

**Core (always installed):**
- `pydantic>=2.5.0`, `pydantic-settings>=2.1.0`
- `fastapi>=0.109.0`, `uvicorn>=0.27.0`, `python-multipart>=0.0.6`
- `httpx>=0.27.0` (W3C API calls — Nu HTML Checker + CSS Validator)
- `rich>=13.7.0`
- `html5lib>=1.1` (local HTML fallback)
- `tinycss2>=1.2.0` (local CSS fallback)
- `esprima>=4.0.0`
- `sqlparse>=0.4.4`
- `ruff>=0.4.0` (subprocess — already a standard dev tool)

**Optional `[llm]`:**
- `anthropic>=0.7.0`

**Optional `[dev]`:**
- `pytest>=7.4.0`, `pytest-cov>=4.1.0`, `httpx>=0.27.0`
- `ruff>=0.4.0`, `basedpyright>=1.8.0`

**Removed from old code-lens:**
- `sqlalchemy`, `alembic`, `aiosqlite` (no DB)
- `python-jose`, `passlib` (no auth)
- `docker` (no sandbox)
- `mypy`, `black`, `isort` (replaced by ruff + basedpyright)
- `structlog` (replaced by stdlib logging)

## Testing

- `tests/unit/` — each `core/` module tested with small synthetic fixture files:
  - valid + invalid Python, HTML, CSS, JS, SQL files generated in `conftest.py` via `tmp_path`
  - no large files committed
- `tests/integration/` — full pipeline with a real zip containing Python + HTML + CSS
  - asserts output validates against `CodeAnalysis` pydantic model
- `tests/api/` — FastAPI `TestClient` hitting `POST /analyse`
  - tests: single file, zip, unsupported type → 422, `--llm` without key → 422

LLM signals are mocked in unit and integration tests. Real LLM calls only in manual smoke tests.

## What Does Not Change

- PyPI package name: `code-analyser`
- Port: 8004
- `src/code_analyser/` module directory (rename from `code_analyser/` if needed)
- Family CLI pattern: `tool-name file.ext [--json]` + `tool-name serve`
