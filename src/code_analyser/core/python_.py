# src/code_analyser/core/python_.py
from __future__ import annotations
import ast
import json
import re
import subprocess
import tempfile
from pathlib import Path

from ..models import LintViolation, PythonMetrics

_TODO_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*$")


def analyse_python(source: str) -> PythonMetrics:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return PythonMetrics(
            syntax_valid=False, lint_error_count=0, lint_warning_count=0,
            lint_violations=[], cyclomatic_complexity=0.0, max_nesting_depth=0,
            loc=0, comment_lines=0, blank_lines=0, function_count=0,
            class_count=0, docstring_coverage=0.0, naming_convention="unknown",
            imports=[], todo_count=0, print_count=0, type_annotation_coverage=0.0,
            has_main_guard=False, bare_except_count=0, comprehension_count=0,
        )

    lines = source.splitlines()
    loc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
    comment_lines = sum(1 for ln in lines if ln.strip().startswith("#"))
    blank_lines = sum(1 for ln in lines if not ln.strip())
    todo_count = sum(1 for ln in lines if _TODO_RE.search(ln))

    visitor = _Visitor()
    visitor.visit(tree)

    violations, err_count, warn_count = _run_ruff(source)
    naming = _detect_naming(visitor.all_names)
    doc_cov = _docstring_coverage(tree)
    type_cov = _type_annotation_coverage(tree)

    return PythonMetrics(
        syntax_valid=True,
        lint_error_count=err_count,
        lint_warning_count=warn_count,
        lint_violations=violations,
        cyclomatic_complexity=visitor.avg_complexity,
        max_nesting_depth=visitor.max_nesting,
        loc=loc,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        function_count=visitor.function_count,
        class_count=visitor.class_count,
        docstring_coverage=doc_cov,
        naming_convention=naming,
        imports=visitor.imports,
        todo_count=todo_count,
        print_count=visitor.print_count,
        type_annotation_coverage=type_cov,
        has_main_guard=visitor.has_main_guard,
        bare_except_count=visitor.bare_except_count,
        comprehension_count=visitor.comprehension_count,
    )


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_count = 0
        self.class_count = 0
        self.imports: list[str] = []
        self.print_count = 0
        self.has_main_guard = False
        self.bare_except_count = 0
        self.comprehension_count = 0
        self.all_names: list[str] = []
        self._complexities: list[int] = []
        self.max_nesting = 0
        self._depth = 0

    @property
    def avg_complexity(self) -> float:
        return sum(self._complexities) / len(self._complexities) if self._complexities else 1.0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_count += 1
        self.all_names.append(node.name)
        cc = 1 + sum(
            1 for child in ast.walk(node)
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With))
        ) + sum(
            len(child.values) - 1 for child in ast.walk(node)
            if isinstance(child, ast.BoolOp)
        )
        self._complexities.append(cc)
        self._depth += 1
        self.max_nesting = max(self.max_nesting, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_count += 1
        self.all_names.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.extend(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.append(node.module)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.print_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if (
            isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            and len(node.test.comparators) == 1
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value == "__main__"
        ):
            self.has_main_guard = True
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.bare_except_count += 1
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.all_names.append(target.id)
        self.generic_visit(node)


def _detect_naming(names: list[str]) -> str:
    if not names:
        return "unknown"
    snake = sum(1 for n in names if _SNAKE_RE.match(n))
    camel = sum(1 for n in names if _CAMEL_RE.match(n))
    total = len(names)
    if snake / total >= 0.75:
        return "snake_case"
    if camel / total >= 0.75:
        return "camelCase"
    if snake > 0 or camel > 0:
        return "mixed"
    return "unknown"


def _docstring_coverage(tree: ast.AST) -> float:
    total = 0
    with_doc = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            total += 1
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                with_doc += 1
    return with_doc / total if total else 0.0


def _type_annotation_coverage(tree: ast.AST) -> float:
    total = 0
    annotated = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            if node.args.vararg:
                args.append(node.args.vararg)
            if node.args.kwarg:
                args.append(node.args.kwarg)
            for arg in args:
                if arg.arg not in ("self", "cls"):
                    total += 1
                    if arg.annotation is not None:
                        annotated += 1
            total += 1  # return type
            if node.returns is not None:
                annotated += 1
    return annotated / total if total else 0.0


_ERROR_PREFIXES = ("F", "B", "E9")  # pyflakes, bugbear, syntax errors


def _run_ruff(source: str) -> tuple[list[LintViolation], int, int]:
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(source)
        tmp = f.name
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", tmp],
            capture_output=True, text=True,
        )
        if result.returncode not in (0, 1):
            return [], 0, 0
        items = json.loads(result.stdout or "[]")
    except (FileNotFoundError, json.JSONDecodeError):
        return [], 0, 0
    finally:
        Path(tmp).unlink(missing_ok=True)

    violations = []
    errors = 0
    warnings = 0
    for item in items:
        code = item.get("code", "")
        line = item.get("location", {}).get("row", 0)
        msg = item.get("message", "")
        violations.append(LintViolation(code=code, line=line, message=msg))
        if any(code.startswith(p) for p in _ERROR_PREFIXES):
            errors += 1
        else:
            warnings += 1
    return violations, errors, warnings
