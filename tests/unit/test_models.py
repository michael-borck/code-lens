from code_analyser.models import (
    LintViolation, PythonMetrics, NotebookMetrics,
    W3CError, W3CCSSError, ExternalResource,
    HTMLMetrics, CSSMetrics, JSMetrics, TSMetrics, SQLMetrics,
    CrossFileSignals, FileLLMSignals, TopLevelLLMSignals,
    FileAnalysis, CodeAnalysis,
)


def test_python_metrics_defaults():
    m = PythonMetrics(
        syntax_valid=True, lint_error_count=0, lint_warning_count=0,
        lint_violations=[], cyclomatic_complexity=1.0, max_nesting_depth=0,
        loc=10, comment_lines=2, blank_lines=1, function_count=1,
        class_count=0, docstring_coverage=1.0, naming_convention="snake_case",
        imports=["os"], todo_count=0, print_count=0,
        type_annotation_coverage=1.0, has_main_guard=False,
        bare_except_count=0, comprehension_count=0,
    )
    assert m.syntax_valid is True
    assert m.naming_convention == "snake_case"


def test_notebook_metrics():
    from code_analyser.models import PythonMetrics
    pm = PythonMetrics(
        syntax_valid=True, lint_error_count=0, lint_warning_count=0,
        lint_violations=[], cyclomatic_complexity=1.0, max_nesting_depth=0,
        loc=5, comment_lines=0, blank_lines=0, function_count=0,
        class_count=0, docstring_coverage=0.0, naming_convention="unknown",
        imports=[], todo_count=0, print_count=1, type_annotation_coverage=0.0,
        has_main_guard=False, bare_except_count=0, comprehension_count=0,
    )
    n = NotebookMetrics(
        code_cell_count=2, markdown_cell_count=1, has_outputs=False,
        output_cell_count=0, execution_order_valid=True, magic_command_count=1,
        python_metrics=pm,
    )
    assert n.code_cell_count == 2
    assert n.python_metrics is not None


def test_html_metrics():
    m = HTMLMetrics(
        syntax_valid=True, parse_error_count=0, validator="local", w3c_errors=[],
        has_doctype=True, semantic_elements_used=["header", "main"],
        semantic_element_count=2, div_count=0, span_count=0,
        div_to_semantic_ratio=None, inline_script_count=0,
        inline_style_count=0, inline_event_handler_count=0, comment_count=0,
        external_scripts=[], external_stylesheets=[], cdn_count=0,
        frameworks_detected=[], img_alt_coverage=1.0, form_label_coverage=1.0,
        has_lang_attr=True, has_title=True, heading_hierarchy_valid=True,
        aria_attribute_count=0, ambiguous_link_count=0,
    )
    assert m.validator == "local"
    assert m.div_to_semantic_ratio is None


def test_css_metrics():
    m = CSSMetrics(
        syntax_valid=True, parse_error_count=0, validator="local",
        w3c_errors=[], w3c_warnings=[], rule_count=3, selector_count=3,
        important_count=0, duplicate_selector_count=0, media_query_count=1,
        custom_property_count=1, comment_count=0, float_count=0,
        flexbox_count=1, grid_count=1, dominant_layout="mixed",
        float_used_for_layout=False,
    )
    assert m.dominant_layout == "mixed"


def test_js_metrics():
    m = JSMetrics(
        syntax_valid=True, parse_error_count=0, function_count=1,
        arrow_function_count=1, async_function_count=1, console_log_count=1,
        import_count=1, comment_coverage=1.0, todo_count=0,
    )
    assert m.function_count == 1


def test_ts_metrics_extends_js():
    m = TSMetrics(
        syntax_valid=True, parse_error_count=0, function_count=2,
        arrow_function_count=1, async_function_count=0, console_log_count=0,
        import_count=1, comment_coverage=0.5, todo_count=0,
        type_annotation_coverage=0.8, interface_count=1, type_alias_count=1,
    )
    assert m.interface_count == 1


def test_sql_metrics():
    m = SQLMetrics(
        statement_count=3, query_types={"SELECT": 2, "INSERT": 1},
        join_count=1, subquery_depth=0, unsafe_patterns=[],
    )
    assert m.query_types["SELECT"] == 2


def test_code_analysis_structure():
    from code_analyser.models import PythonMetrics, FileAnalysis, CrossFileSignals, CodeAnalysis
    pm = PythonMetrics(
        syntax_valid=True, lint_error_count=0, lint_warning_count=0,
        lint_violations=[], cyclomatic_complexity=1.0, max_nesting_depth=0,
        loc=10, comment_lines=2, blank_lines=1, function_count=1,
        class_count=0, docstring_coverage=1.0, naming_convention="snake_case",
        imports=[], todo_count=0, print_count=0, type_annotation_coverage=1.0,
        has_main_guard=False, bare_except_count=0, comprehension_count=0,
    )
    fa = FileAnalysis(filename="app.py", language="python", metrics=pm, llm_signals=None)
    cf = CrossFileSignals(
        file_count=1, languages_detected=["python"], import_graph={},
        unrecognised_files=[], has_package_json=False, frameworks_detected=[],
    )
    ca = CodeAnalysis(input="app.py", file_count=1, languages_detected=["python"],
                      files=[fa], cross_file=cf, llm_signals=None)
    assert ca.file_count == 1
    assert ca.files[0].language == "python"
