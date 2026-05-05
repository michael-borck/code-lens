from __future__ import annotations
import re

import httpx
import tinycss2

from ..models import CSSMetrics, W3CCSSError


def _w3c_validate_css(source: str, timeout: float) -> tuple[list[W3CCSSError], list[W3CCSSError]]:
    resp = httpx.get(
        "https://jigsaw.w3.org/css-validator/validator",
        params={"text": source, "output": "json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json().get("cssvalidation", {})
    errors = [W3CCSSError(line=e.get("line", 0), message=e.get("message", "")) for e in data.get("errors", [])]
    warnings = [W3CCSSError(line=w.get("line", 0), message=w.get("message", "")) for w in data.get("warnings", [])]
    return errors, warnings


_LAYOUT_FLOAT_SELECTOR = re.compile(r"img|figure|picture", re.I)


def _count_declarations(declarations, counters: dict) -> None:
    for token in declarations:
        if token.type != "declaration":
            continue
        name = token.lower_name
        value_str = tinycss2.serialize(token.value).strip()
        if token.important:
            counters["important"] += 1
        if name.startswith("--"):
            counters["custom_props"] += 1
        if name == "float" and value_str.lower() in ("left", "right"):
            counters["float"] += 1
        if name == "display":
            if "flex" in value_str:
                counters["flex"] += 1
            elif "grid" in value_str:
                counters["grid"] += 1


def _dominant(floats: int, flex: int, grid: int) -> str:
    total = floats + flex + grid
    if total == 0:
        return "none"
    counts = {"float": floats, "flexbox": flex, "grid": grid}
    top = max(counts, key=lambda k: counts[k])
    top_val = counts[top]
    others = [v for k, v in counts.items() if k != top]
    if any(top_val > 0 and o / top_val >= 0.8 for o in others if o > 0):
        return "mixed"
    return top


def analyse_css(source: str, *, timeout: float = 5.0) -> CSSMetrics:
    w3c_errors: list[W3CCSSError] = []
    w3c_warnings: list[W3CCSSError] = []
    validator = "local"
    try:
        w3c_errors, w3c_warnings = _w3c_validate_css(source, timeout)
        validator = "w3c"
    except (httpx.RequestError, httpx.HTTPStatusError):
        pass

    rules_raw = tinycss2.parse_stylesheet(source, skip_comments=False, skip_whitespace=True)
    parse_errors = [r for r in rules_raw if r.type == "error"]

    counters = {"important": 0, "custom_props": 0, "float": 0, "flex": 0, "grid": 0}
    rule_count = 0
    selector_count = 0
    media_query_count = 0
    comment_count = 0
    seen_selectors: dict[str, int] = {}
    float_selectors: list[str] = []

    for rule in rules_raw:
        if rule.type == "comment":
            comment_count += 1
        elif rule.type == "qualified-rule":
            rule_count += 1
            sel = tinycss2.serialize(rule.prelude).strip()
            selector_count += 1
            seen_selectors[sel] = seen_selectors.get(sel, 0) + 1
            decls = tinycss2.parse_declaration_list(rule.content, skip_whitespace=True)
            before = counters["float"]
            _count_declarations(decls, counters)
            if counters["float"] > before:
                float_selectors.append(sel)
        elif rule.type == "at-rule" and rule.lower_at_keyword == "media":
            media_query_count += 1
            if rule.content:
                sub = tinycss2.parse_stylesheet(
                    tinycss2.serialize(rule.content), skip_whitespace=True
                )
                for sub_rule in sub:
                    if sub_rule.type == "qualified-rule":
                        rule_count += 1
                        sel = tinycss2.serialize(sub_rule.prelude).strip()
                        selector_count += 1
                        seen_selectors[sel] = seen_selectors.get(sel, 0) + 1
                        decls = tinycss2.parse_declaration_list(sub_rule.content, skip_whitespace=True)
                        before = counters["float"]
                        _count_declarations(decls, counters)
                        if counters["float"] > before:
                            float_selectors.append(sel)

    duplicate_selector_count = sum(1 for c in seen_selectors.values() if c > 1)

    float_used_for_layout = any(
        not _LAYOUT_FLOAT_SELECTOR.search(sel) for sel in float_selectors
    )

    return CSSMetrics(
        syntax_valid=len(parse_errors) == 0,
        parse_error_count=len(parse_errors),
        validator=validator,
        w3c_errors=w3c_errors,
        w3c_warnings=w3c_warnings,
        rule_count=rule_count,
        selector_count=selector_count,
        important_count=counters["important"],
        duplicate_selector_count=duplicate_selector_count,
        media_query_count=media_query_count,
        custom_property_count=counters["custom_props"],
        comment_count=comment_count,
        float_count=counters["float"],
        flexbox_count=counters["flex"],
        grid_count=counters["grid"],
        dominant_layout=_dominant(counters["float"], counters["flex"], counters["grid"]),
        float_used_for_layout=float_used_for_layout,
    )
