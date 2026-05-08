"""Validation-focused tests for the public Pydantic models.

This file used to be wall-to-wall echo-constructor tests ("construct with
literal X, assert literal X back") — those are tautological because Pydantic
already round-trips literals by definition. The trimmed file below keeps a
couple of shape-validation cases and adds two real validator tests that
exercise the constraints in models.py.
"""

import pytest
from pydantic import ValidationError

from code_analyser.models import (
    CSSMetrics,
    HTMLMetrics,
    NotebookMetrics,
    PythonMetrics,
)


def _python_metrics_kwargs(**overrides) -> dict:
    """Minimal valid PythonMetrics kwargs; override any field per-test."""
    base = dict(
        syntax_valid=True,
        lint_error_count=0,
        lint_warning_count=0,
        lint_violations=[],
        cyclomatic_complexity=1.0,
        max_nesting_depth=0,
        loc=10,
        comment_lines=2,
        blank_lines=1,
        function_count=1,
        class_count=0,
        docstring_coverage=1.0,
        naming_convention="snake_case",
        imports=["os"],
        todo_count=0,
        print_count=0,
        type_annotation_coverage=1.0,
        has_main_guard=False,
        bare_except_count=0,
        comprehension_count=0,
    )
    base.update(overrides)
    return base


def _html_metrics_kwargs(**overrides) -> dict:
    base = dict(
        syntax_valid=True,
        parse_error_count=0,
        validator="local",
        w3c_errors=[],
        has_doctype=True,
        semantic_elements_used=[],
        semantic_element_count=0,
        div_count=0,
        span_count=0,
        div_to_semantic_ratio=None,
        inline_script_count=0,
        inline_style_count=0,
        inline_event_handler_count=0,
        comment_count=0,
        external_scripts=[],
        external_stylesheets=[],
        cdn_count=0,
        frameworks_detected=[],
        img_alt_coverage=1.0,
        form_label_coverage=1.0,
        has_lang_attr=True,
        has_title=True,
        heading_hierarchy_valid=True,
        aria_attribute_count=0,
        ambiguous_link_count=0,
    )
    base.update(overrides)
    return base


def test_python_metrics_default_values():
    """A valid construction round-trips and naming_convention enum holds."""
    m = PythonMetrics(**_python_metrics_kwargs())
    # Spot-check a handful of fields — not the full echo battery.
    assert m.syntax_valid is True
    assert m.naming_convention == "snake_case"
    assert m.lint_violations == []  # list default preserved


def test_notebook_metrics_default_python_metrics_is_none():
    """NotebookMetrics.python_metrics defaults to None when omitted."""
    n = NotebookMetrics(
        code_cell_count=2,
        markdown_cell_count=1,
        has_outputs=False,
        output_cell_count=0,
        execution_order_valid=True,
        magic_command_count=1,
    )
    assert n.python_metrics is None
    assert n.code_cell_count == 2


def test_html_metrics_default_construction():
    """HTMLMetrics constructs with a valid 'local' validator and minimal fields."""
    m = HTMLMetrics(**_html_metrics_kwargs())
    assert m.validator == "local"
    assert m.div_to_semantic_ratio is None


def test_python_metrics_rejects_negative_loc():
    """PythonMetrics.loc has Field(ge=0); negative values must be rejected."""
    with pytest.raises(ValidationError):
        PythonMetrics(**_python_metrics_kwargs(loc=-1))


def test_html_metrics_rejects_invalid_validator_literal():
    """HTMLMetrics.validator is Literal["w3c", "local"]; bogus values rejected."""
    with pytest.raises(ValidationError):
        HTMLMetrics(**_html_metrics_kwargs(validator="bogus"))


def test_css_metrics_rejects_invalid_dominant_layout():
    """CSSMetrics.dominant_layout is a closed Literal; bogus values rejected."""
    with pytest.raises(ValidationError):
        CSSMetrics(
            syntax_valid=True,
            parse_error_count=0,
            validator="local",
            w3c_errors=[],
            w3c_warnings=[],
            rule_count=0,
            selector_count=0,
            important_count=0,
            duplicate_selector_count=0,
            media_query_count=0,
            custom_property_count=0,
            comment_count=0,
            float_count=0,
            flexbox_count=0,
            grid_count=0,
            dominant_layout="bogus",  # invalid Literal
            float_used_for_layout=False,
        )
