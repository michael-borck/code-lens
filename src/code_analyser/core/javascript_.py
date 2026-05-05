from __future__ import annotations
import re

try:
    import esprima
    _ESPRIMA_AVAILABLE = True
except ImportError:
    _ESPRIMA_AVAILABLE = False

from ..models import JSMetrics

_TODO_RE = re.compile(r"//\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_COMMENT_LINE_RE = re.compile(r"^\s*(?://|/\*|\*)", re.MULTILINE)


def analyse_javascript(source: str, *, jsx: bool = False) -> JSMetrics:
    if not _ESPRIMA_AVAILABLE:
        return _fallback_metrics(source)

    opts = {"tolerant": True, "comment": True}
    tree = None
    parse_failed = False
    try:
        tree = esprima.parseModule(source, **opts)
    except Exception:
        try:
            tree = esprima.parseScript(source, **opts)
        except Exception:
            parse_failed = True

    if parse_failed or tree is None:
        return JSMetrics(
            syntax_valid=False, parse_error_count=1,
            function_count=0, arrow_function_count=0, async_function_count=0,
            console_log_count=0, import_count=0, comment_coverage=0.0, todo_count=0,
        )

    parse_error_count = len(getattr(tree, "errors", []))
    syntax_valid = parse_error_count == 0

    counts = _walk(tree)
    todo_count = len(_TODO_RE.findall(source))
    comment_lines = len(_COMMENT_LINE_RE.findall(source))
    total_fns = counts["functions"] + counts["arrows"]
    comment_coverage = min(comment_lines / max(total_fns, 1), 1.0)

    return JSMetrics(
        syntax_valid=syntax_valid,
        parse_error_count=parse_error_count,
        function_count=counts["functions"],
        arrow_function_count=counts["arrows"],
        async_function_count=counts["async"],
        console_log_count=counts["console_logs"],
        import_count=counts["imports"],
        comment_coverage=comment_coverage,
        todo_count=todo_count,
    )


def _fallback_metrics(source: str) -> JSMetrics:
    todo_count = len(_TODO_RE.findall(source))
    return JSMetrics(
        syntax_valid=True, parse_error_count=0,
        function_count=len(re.findall(r"\bfunction\s+\w+\s*\(", source)),
        arrow_function_count=len(re.findall(r"=>\s*[{(]", source)),
        async_function_count=len(re.findall(r"\basync\s+(?:function|\w+\s*=>|\()", source)),
        console_log_count=len(re.findall(r"\bconsole\.log\s*\(", source)),
        import_count=len(re.findall(r"\bimport\s+", source)),
        comment_coverage=0.0,
        todo_count=todo_count,
    )


def _walk(node) -> dict[str, int]:
    counts = {"functions": 0, "arrows": 0, "async": 0, "console_logs": 0, "imports": 0}

    def visit(n):
        if not hasattr(n, "type"):
            return
        t = n.type
        if t in ("FunctionDeclaration", "FunctionExpression"):
            counts["functions"] += 1
            if getattr(n, "isAsync", False) or getattr(n, "async", False):
                counts["async"] += 1
        elif t == "ArrowFunctionExpression":
            counts["arrows"] += 1
            if getattr(n, "isAsync", False) or getattr(n, "async", False):
                counts["async"] += 1
        elif t == "ImportDeclaration":
            counts["imports"] += 1
        elif t == "CallExpression":
            callee = getattr(n, "callee", None)
            if (callee and getattr(callee, "type", "") == "MemberExpression"
                    and getattr(getattr(callee, "object", None), "name", "") == "console"
                    and getattr(getattr(callee, "property", None), "name", "") == "log"):
                counts["console_logs"] += 1
            if (getattr(callee, "type", "") == "Identifier"
                    and getattr(callee, "name", "") == "require"):
                counts["imports"] += 1

        for key in vars(n):
            child = getattr(n, key)
            if hasattr(child, "type"):
                visit(child)
            elif isinstance(child, list):
                for item in child:
                    if hasattr(item, "type"):
                        visit(item)

    visit(node)
    return counts
