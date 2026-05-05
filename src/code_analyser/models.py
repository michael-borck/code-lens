from __future__ import annotations
from typing import Union
from pydantic import BaseModel


class LintViolation(BaseModel):
    code: str
    line: int
    message: str


class PythonMetrics(BaseModel):
    syntax_valid: bool
    lint_error_count: int
    lint_warning_count: int
    lint_violations: list[LintViolation]
    cyclomatic_complexity: float
    max_nesting_depth: int
    loc: int
    comment_lines: int
    blank_lines: int
    function_count: int
    class_count: int
    docstring_coverage: float
    naming_convention: str  # "snake_case" | "camelCase" | "mixed" | "unknown"
    imports: list[str]
    todo_count: int
    print_count: int
    type_annotation_coverage: float
    has_main_guard: bool
    bare_except_count: int
    comprehension_count: int


class NotebookMetrics(BaseModel):
    code_cell_count: int
    markdown_cell_count: int
    has_outputs: bool
    output_cell_count: int
    execution_order_valid: bool
    magic_command_count: int
    python_metrics: PythonMetrics | None


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
    parse_error_count: int
    validator: str  # "w3c" | "local"
    w3c_errors: list[W3CError]
    has_doctype: bool
    semantic_elements_used: list[str]
    semantic_element_count: int
    div_count: int
    span_count: int
    div_to_semantic_ratio: float | None
    inline_script_count: int
    inline_style_count: int
    inline_event_handler_count: int
    comment_count: int
    external_scripts: list[ExternalResource]
    external_stylesheets: list[ExternalResource]
    cdn_count: int
    frameworks_detected: list[str]
    img_alt_coverage: float
    form_label_coverage: float
    has_lang_attr: bool
    has_title: bool
    heading_hierarchy_valid: bool
    aria_attribute_count: int
    ambiguous_link_count: int


class CSSMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: int
    validator: str  # "w3c" | "local"
    w3c_errors: list[W3CCSSError]
    w3c_warnings: list[W3CCSSError]
    rule_count: int
    selector_count: int
    important_count: int
    duplicate_selector_count: int
    media_query_count: int
    custom_property_count: int
    comment_count: int
    float_count: int
    flexbox_count: int
    grid_count: int
    dominant_layout: str  # "float" | "flexbox" | "grid" | "mixed" | "none"
    float_used_for_layout: bool


class JSMetrics(BaseModel):
    syntax_valid: bool
    parse_error_count: int
    function_count: int
    arrow_function_count: int
    async_function_count: int
    console_log_count: int
    import_count: int
    comment_coverage: float
    todo_count: int


class TSMetrics(JSMetrics):
    type_annotation_coverage: float
    interface_count: int
    type_alias_count: int


class SQLMetrics(BaseModel):
    statement_count: int
    query_types: dict[str, int]
    join_count: int
    subquery_depth: int
    unsafe_patterns: list[str]


class CrossFileSignals(BaseModel):
    file_count: int
    languages_detected: list[str]
    import_graph: dict[str, list[str]]
    unrecognised_files: list[str]
    has_package_json: bool
    frameworks_detected: list[str]


class FileLLMSignals(BaseModel):
    comment_quality: str
    naming_quality: str
    style_guide: str | None
    code_level: str  # "beginner" | "intermediate" | "advanced"
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
