"""
Base analyzer interface and common functionality
"""

import ast
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(Enum):
    """Issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AnalysisIssue:
    """Represents an issue found during analysis"""
    line: int
    column: int = 0
    severity: Severity = Severity.WARNING
    code: str = ""  # Error/warning code (e.g., "E501", "W292")
    message: str = ""
    category: str = "general"  # style, syntax, logic, complexity, etc.
    suggestion: str | None = None  # How to fix the issue


@dataclass
class CodeMetrics:
    """Code quality metrics"""
    lines_of_code: int = 0
    lines_of_comments: int = 0
    blank_lines: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    function_count: int = 0
    class_count: int = 0
    max_nesting_depth: int = 0
    maintainability_index: float = 0.0


@dataclass
class AnalysisResult:
    """Results from code analysis"""
    success: bool
    issues: list[AnalysisIssue]
    metrics: CodeMetrics
    execution_time: float = 0.0
    analyzer_version: str = ""
    raw_output: str | None = None  # Raw analyzer output for debugging


class BaseAnalyzer(ABC):
    """Base class for all code analyzers"""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    async def analyze(self, code: str, file_path: str = "temp.py") -> AnalysisResult:
        """
        Analyze the given code and return results

        Args:
            code: Source code to analyze
            file_path: Optional file path for context

        Returns:
            AnalysisResult with issues and metrics
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get the version of the analyzer tool"""
        pass

    def get_code_hash(self, code: str) -> str:
        """Generate SHA-256 hash of code for caching/identification"""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def parse_ast(self, code: str) -> ast.AST | None:
        """Parse code into AST, return None if syntax error"""
        try:
            return ast.parse(code)
        except SyntaxError:
            return None

    def calculate_basic_metrics(self, code: str) -> CodeMetrics:
        """Calculate basic code metrics from source"""
        lines = code.split('\n')

        metrics = CodeMetrics()
        metrics.lines_of_code = len([line for line in lines if line.strip()])
        metrics.blank_lines = len([line for line in lines if not line.strip()])
        metrics.lines_of_comments = len([
            line for line in lines
            if line.strip().startswith('#') and not line.strip().startswith('#!')
        ])

        # Try to get AST metrics
        try:
            tree = ast.parse(code)
            metrics.function_count = len([
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ])
            metrics.class_count = len([
                node for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            ])
            metrics.max_nesting_depth = self._calculate_nesting_depth(tree)
        except SyntaxError:
            pass  # Keep default values if code doesn't parse

        return metrics

    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth in AST"""
        max_depth = current_depth

        # Nodes that increase nesting depth
        nesting_nodes = (ast.If, ast.While, ast.For, ast.With, ast.Try)

        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth
