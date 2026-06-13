from __future__ import annotations
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

__all__ = [
    "LintViolation", "PythonMetrics", "NotebookMetrics",
    "W3CError", "W3CCSSError", "ExternalResource",
    "HTMLMetrics", "CSSMetrics", "JSMetrics", "TSMetrics", "SQLMetrics",
    "CrossFileSignals", "FileLLMSignals", "TopLevelLLMSignals",
    "FileMetrics", "FileAnalysis", "CodeAnalysis",
]


class LintViolation(BaseModel):
    code: str
    line: int
    message: str


class PythonMetrics(BaseModel):
    syntax_valid: bool
    lint_error_count: Annotated[int, Field(ge=0)]
    lint_warning_count: Annotated[int, Field(ge=0)]
    lint_violations: list[LintViolation]
    cyclomatic_complexity: Annotated[float, Field(ge=0.0)]
    max_nesting_depth: Annotated[int, Field(ge=0)]
    loc: Annotated[int, Field(ge=0)]
    comment_lines: Annotated[int, Field(ge=0)]
    blank_lines: Annotated[int, Field(ge=0)]
    function_count: Annotated[int, Field(ge=0)]
    class_count: Annotated[int, Field(ge=0)]
    docstring_coverage: Annotated[float, Field(ge=0.0)]
    naming_convention: Literal["snake_case", "camelCase", "mixed", "unknown"]
    imports: list[str]
    todo_count: Annotated[int, Field(ge=0)]
    print_count: Annotated[int, Field(ge=0)]
    type_annotation_coverage: Annotated[float, Field(ge=0.0)]
    has_main_guard: bool
    bare_except_count: Annotated[int, Field(ge=0)]
    comprehension_count: Annotated[int, Field(ge=0)]


class NotebookMetrics(BaseModel):
    code_cell_count: Annotated[int, Field(ge=0)]
    markdown_cell_count: Annotated[int, Field(ge=0)]
    has_outputs: bool
    output_cell_count: Annotated[int, Field(ge=0)]
    execution_order_valid: bool
    magic_command_count: Annotated[int, Field(ge=0)]
    python_metrics: PythonMetrics | None = None


class W3CError(BaseModel):
    type: str
    line: int
    message: str


class W3CCSSError(BaseModel):
    line: int
    message: str


class ExternalResource(BaseModel):
    src: str
    is_cdn: bool
    library: str | None


class HTMLMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: Annotated[int, Field(ge=0)]
    validator: Literal["w3c", "local"]
    w3c_errors: list[W3CError]
    has_doctype: bool
    semantic_elements_used: list[str]
    semantic_element_count: Annotated[int, Field(ge=0)]
    div_count: Annotated[int, Field(ge=0)]
    span_count: Annotated[int, Field(ge=0)]
    div_to_semantic_ratio: float | None
    inline_script_count: Annotated[int, Field(ge=0)]
    inline_style_count: Annotated[int, Field(ge=0)]
    inline_event_handler_count: Annotated[int, Field(ge=0)]
    comment_count: Annotated[int, Field(ge=0)]
    external_scripts: list[ExternalResource]
    external_stylesheets: list[ExternalResource]
    cdn_count: Annotated[int, Field(ge=0)]
    frameworks_detected: list[str]
    img_alt_coverage: Annotated[float, Field(ge=0.0)]
    form_label_coverage: Annotated[float, Field(ge=0.0)]
    has_lang_attr: bool
    has_title: bool
    heading_hierarchy_valid: bool
    aria_attribute_count: Annotated[int, Field(ge=0)]
    ambiguous_link_count: Annotated[int, Field(ge=0)]


class CSSMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: Annotated[int, Field(ge=0)]
    validator: Literal["w3c", "local"]
    w3c_errors: list[W3CCSSError]
    w3c_warnings: list[W3CCSSError]
    rule_count: Annotated[int, Field(ge=0)]
    selector_count: Annotated[int, Field(ge=0)]
    important_count: Annotated[int, Field(ge=0)]
    duplicate_selector_count: Annotated[int, Field(ge=0)]
    media_query_count: Annotated[int, Field(ge=0)]
    custom_property_count: Annotated[int, Field(ge=0)]
    comment_count: Annotated[int, Field(ge=0)]
    float_count: Annotated[int, Field(ge=0)]
    flexbox_count: Annotated[int, Field(ge=0)]
    grid_count: Annotated[int, Field(ge=0)]
    dominant_layout: Literal["float", "flexbox", "grid", "mixed", "none"]
    float_used_for_layout: bool


class JSMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: Annotated[int, Field(ge=0)]
    function_count: Annotated[int, Field(ge=0)]
    arrow_function_count: Annotated[int, Field(ge=0)]
    async_function_count: Annotated[int, Field(ge=0)]
    console_log_count: Annotated[int, Field(ge=0)]
    import_count: Annotated[int, Field(ge=0)]
    comment_coverage: Annotated[float, Field(ge=0.0)]
    todo_count: Annotated[int, Field(ge=0)]


class TSMetrics(JSMetrics):
    syntax_valid: bool = Field(
        description=(
            "For TypeScript, this is a brace-balance heuristic "
            "(open vs close `{}` within ±3), NOT parser-based. "
            "A real TS parser would catch syntax errors this misses."
        ),
    )
    type_annotation_coverage: Annotated[float, Field(ge=0.0)]
    interface_count: Annotated[int, Field(ge=0)]
    type_alias_count: Annotated[int, Field(ge=0)]


class SQLMetrics(BaseModel):
    statement_count: Annotated[int, Field(ge=0)]
    query_types: dict[str, int]
    join_count: Annotated[int, Field(ge=0)]
    subquery_depth: Annotated[int, Field(ge=0)]
    unsafe_patterns: list[str]


class CrossFileSignals(BaseModel):
    file_count: Annotated[int, Field(ge=0)]
    languages_detected: list[str]
    import_graph: dict[str, list[str]]
    unrecognised_files: list[str]
    has_package_json: bool
    frameworks_detected: list[str]


class FileLLMSignals(BaseModel):
    comment_quality: str
    naming_quality: str
    style_guide: str | None
    code_level: Literal["beginner", "intermediate", "advanced"]
    self_documenting_score: float
    suggestions: list[str]


class TopLevelLLMSignals(BaseModel):
    overall_quality: str
    consistency: str


FileMetrics = Union[
    PythonMetrics, NotebookMetrics, HTMLMetrics, CSSMetrics,
    JSMetrics, TSMetrics, SQLMetrics,
]


class FileAnalysis(BaseModel):
    filename: str
    language: str
    metrics: FileMetrics | None = None
    llm_signals: FileLLMSignals | None = None


class CodeAnalysis(BaseModel):
    input: str
    file_count: int
    languages_detected: list[str]
    files: list[FileAnalysis]
    cross_file: CrossFileSignals
    llm_signals: TopLevelLLMSignals | None = None
    # Pooled, L2-normalised source vector from lens-embed (pinned all-MiniLM-L6-v2).
    # Comparable across members; None unless [embeddings] installed.
    embedding: list[float] | None = None
