from __future__ import annotations
import re

from ..models import TSMetrics

_FUNC_RE = re.compile(r"\bfunction\s+\w+\s*\(", re.MULTILINE)
_ARROW_RE = re.compile(
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*\w[\w<>\[\]|&,\s]*?)?\s*=>",
    re.MULTILINE,
)
_ASYNC_RE = re.compile(
    r"\basync\s+(?:function\s+\w+|\w+\s*=>|\([^)]*\)\s*=>)", re.MULTILINE
)
_CONSOLE_RE = re.compile(r"\bconsole\.log\s*\(")
_IMPORT_RE = re.compile(r"\bimport\s+")
_INTERFACE_RE = re.compile(r"\binterface\s+\w+")
_TYPE_ALIAS_RE = re.compile(r"\btype\s+\w+\s*=")
_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*)", re.MULTILINE)
_TODO_RE = re.compile(r"//\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_TYPED_PARAM_RE = re.compile(
    r"\w+\s*\??\s*:\s*(?:[A-Z]\w*|string|number|boolean|any|void|never|unknown|object)"
)
_RETURN_TYPE_RE = re.compile(
    r"\)\s*:\s*(?:[A-Z]\w*|string|number|boolean|any|void|never|unknown|object)[\s{;=]"
)


def analyse_typescript(source: str, *, tsx: bool = False) -> TSMetrics:
    syntax_valid = abs(source.count("{") - source.count("}")) <= 3

    function_count = len(_FUNC_RE.findall(source))
    arrow_count = len(_ARROW_RE.findall(source))
    async_count = len(_ASYNC_RE.findall(source))
    console_log = len(_CONSOLE_RE.findall(source))
    import_count = len(_IMPORT_RE.findall(source))
    interface_count = len(_INTERFACE_RE.findall(source))
    type_alias_count = len(_TYPE_ALIAS_RE.findall(source))
    todo_count = len(_TODO_RE.findall(source))

    comment_lines = len(_COMMENT_RE.findall(source))
    total_fns = function_count + arrow_count
    comment_coverage = min(comment_lines / max(total_fns, 1), 1.0)

    typed_params = len(_TYPED_PARAM_RE.findall(source))
    return_types = len(_RETURN_TYPE_RE.findall(source))
    type_annotation_coverage = min(
        (typed_params + return_types) / max(total_fns * 2 + interface_count, 1), 1.0
    )

    return TSMetrics(
        syntax_valid=syntax_valid,
        parse_error_count=0,
        function_count=function_count,
        arrow_function_count=arrow_count,
        async_function_count=async_count,
        console_log_count=console_log,
        import_count=import_count,
        comment_coverage=comment_coverage,
        todo_count=todo_count,
        type_annotation_coverage=type_annotation_coverage,
        interface_count=interface_count,
        type_alias_count=type_alias_count,
    )
