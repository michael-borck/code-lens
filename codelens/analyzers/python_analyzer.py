"""
Python code analyzer using ruff and mypy
"""

import ast
import asyncio
import json
import os
import tempfile
import time
from typing import Any

import structlog

from .base import AnalysisIssue, AnalysisResult, BaseAnalyzer, Severity

logger = structlog.get_logger()


class PythonAnalyzer(BaseAnalyzer):
    """Python code analyzer using ruff (linting/formatting) and mypy (type checking)"""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        # Default configuration
        self.ruff_enabled = self.config.get("ruff_enabled", True)
        self.mypy_enabled = self.config.get("mypy_enabled", True)
        self.ruff_config = self.config.get("ruff_config")  # Path to ruff config file
        self.mypy_config = self.config.get("mypy_config")  # Path to mypy config file

        # Analysis options
        self.max_line_length = self.config.get("max_line_length", 88)
        self.check_type_hints = self.config.get("check_type_hints", True)
        self.check_docstrings = self.config.get("check_docstrings", True)

    async def analyze(self, code: str, file_path: str = "temp.py") -> AnalysisResult:
        """Analyze Python code using ruff and mypy"""
        start_time = time.time()

        issues: list[AnalysisIssue] = []
        metrics = self.calculate_basic_metrics(code)

        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            # Run ruff analysis
            if self.ruff_enabled:
                ruff_issues = await self._run_ruff(temp_file_path, code)
                issues.extend(ruff_issues)

            # Run mypy analysis
            if self.mypy_enabled and self.check_type_hints:
                mypy_issues = await self._run_mypy(temp_file_path, code)
                issues.extend(mypy_issues)

            # Calculate advanced metrics
            advanced_metrics = await self._calculate_advanced_metrics(code)
            metrics.cyclomatic_complexity = advanced_metrics.get("cyclomatic_complexity", 0)
            metrics.cognitive_complexity = advanced_metrics.get("cognitive_complexity", 0)
            metrics.maintainability_index = advanced_metrics.get("maintainability_index", 0.0)

            execution_time = time.time() - start_time

            return AnalysisResult(
                success=True,
                issues=issues,
                metrics=metrics,
                execution_time=execution_time,
                analyzer_version=self.get_version()
            )

        except Exception as e:
            logger.error("Python analysis failed", error=str(e), file_path=file_path)
            return AnalysisResult(
                success=False,
                issues=[AnalysisIssue(
                    line=1,
                    severity=Severity.ERROR,
                    code="ANALYZER_ERROR",
                    message=f"Analysis failed: {str(e)}",
                    category="system"
                )],
                metrics=metrics,
                execution_time=time.time() - start_time,
                analyzer_version=self.get_version()
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    async def _run_ruff(self, file_path: str, code: str) -> list[AnalysisIssue]:
        """Run ruff linter and formatter checks"""
        issues: list[AnalysisIssue] = []

        try:
            # Build ruff command
            cmd = ["ruff", "check", "--output-format=json"]

            if self.ruff_config:
                cmd.extend(["--config", self.ruff_config])
            else:
                # Use inline configuration
                cmd.extend([
                    "--line-length", str(self.max_line_length),
                    "--select", "E,W,F,B,C4,UP,I",  # Error categories
                ])

            cmd.append(file_path)

            # Run ruff
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # No issues found
                pass
            elif process.returncode == 1:
                # Issues found - parse JSON output
                try:
                    ruff_results = json.loads(stdout.decode())
                    for result in ruff_results:
                        issues.append(AnalysisIssue(
                            line=result.get("location", {}).get("row", 1),
                            column=result.get("location", {}).get("column", 0),
                            severity=self._map_ruff_severity(result.get("code", "")),
                            code=result.get("code", ""),
                            message=result.get("message", ""),
                            category="style" if result.get("code", "").startswith(("E", "W")) else "logic",
                            suggestion=result.get("fix", {}).get("message") if result.get("fix") else None
                        ))
                except json.JSONDecodeError:
                    logger.warning("Failed to parse ruff JSON output", stdout=stdout.decode())

            else:
                # Error running ruff
                logger.error("Ruff execution failed",
                           returncode=process.returncode,
                           stderr=stderr.decode())

        except FileNotFoundError:
            logger.warning("Ruff not found - skipping ruff analysis")
            issues.append(AnalysisIssue(
                line=1,
                severity=Severity.WARNING,
                code="TOOL_MISSING",
                message="Ruff not installed - style checking skipped",
                category="system"
            ))
        except Exception as e:
            logger.error("Ruff analysis error", error=str(e))

        return issues

    async def _run_mypy(self, file_path: str, code: str) -> list[AnalysisIssue]:
        """Run mypy type checker"""
        issues: list[AnalysisIssue] = []

        try:
            # Build mypy command
            cmd = ["mypy", "--show-error-codes", "--no-error-summary", "--output", "json"]

            if self.mypy_config:
                cmd.extend(["--config-file", self.mypy_config])
            else:
                # Basic mypy settings
                cmd.extend([
                    "--check-untyped-defs",
                    "--disallow-untyped-defs",
                    "--warn-return-any",
                ])

            cmd.append(file_path)

            # Run mypy
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # No type issues
                pass
            else:
                # Parse mypy JSON output
                try:
                    for line in stdout.decode().strip().split('\n'):
                        if line.strip():
                            mypy_result = json.loads(line)
                            issues.append(AnalysisIssue(
                                line=mypy_result.get("line", 1),
                                column=mypy_result.get("column", 0),
                                severity=self._map_mypy_severity(mypy_result.get("severity", "error")),
                                code=mypy_result.get("code", ""),
                                message=mypy_result.get("message", ""),
                                category="types"
                            ))
                except (json.JSONDecodeError, KeyError):
                    # Fallback to parsing text output
                    self._parse_mypy_text_output(stdout.decode(), issues)

        except FileNotFoundError:
            logger.warning("Mypy not found - skipping type checking")
            issues.append(AnalysisIssue(
                line=1,
                severity=Severity.INFO,
                code="TOOL_MISSING",
                message="Mypy not installed - type checking skipped",
                category="system"
            ))
        except Exception as e:
            logger.error("Mypy analysis error", error=str(e))

        return issues

    def _map_ruff_severity(self, code: str) -> Severity:
        """Map ruff error codes to severity levels"""
        if code.startswith("F"):  # pyflakes - logical errors
            return Severity.ERROR
        elif code.startswith("E"):  # pycodestyle errors
            return Severity.WARNING
        elif code.startswith("W"):  # pycodestyle warnings
            return Severity.INFO
        elif code.startswith("B"):  # flake8-bugbear - likely bugs
            return Severity.ERROR
        else:
            return Severity.WARNING

    def _map_mypy_severity(self, severity: str) -> Severity:
        """Map mypy severity to our severity levels"""
        return {
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "note": Severity.INFO
        }.get(severity.lower(), Severity.WARNING)

    def _parse_mypy_text_output(self, output: str, issues: list[AnalysisIssue]) -> None:
        """Parse mypy text output when JSON parsing fails"""
        for line in output.strip().split('\n'):
            if ':' in line and ('error:' in line or 'warning:' in line):
                try:
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        line_num = int(parts[1]) if parts[1].isdigit() else 1
                        severity_text = "error" if "error:" in line else "warning"
                        message = parts[3].strip()

                        issues.append(AnalysisIssue(
                            line=line_num,
                            severity=self._map_mypy_severity(severity_text),
                            message=message,
                            category="types"
                        ))
                except (ValueError, IndexError):
                    continue

    async def _calculate_advanced_metrics(self, code: str) -> dict[str, Any]:
        """Calculate advanced code metrics using radon or custom analysis"""
        metrics = {}

        try:
            # Try to use radon for complexity metrics
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            # Cyclomatic complexity with radon
            process = await asyncio.create_subprocess_exec(
                "radon", "cc", "--json", temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                radon_results = json.loads(stdout.decode())
                max_complexity = 0
                for file_results in radon_results.values():
                    for item in file_results:
                        max_complexity = max(max_complexity, item.get('complexity', 0))
                metrics['cyclomatic_complexity'] = max_complexity

            os.unlink(temp_file_path)

        except (FileNotFoundError, Exception):
            # Fallback to basic AST analysis
            metrics.update(self._calculate_ast_complexity(code))

        return metrics

    def _calculate_ast_complexity(self, code: str) -> dict[str, Any]:
        """Calculate complexity metrics using AST analysis"""
        try:
            tree = ast.parse(code)
            complexity = self._calculate_cyclomatic_complexity(tree)
            return {
                'cyclomatic_complexity': complexity,
                'cognitive_complexity': complexity,  # Simplified
                'maintainability_index': max(0, 171 - 5.2 * complexity - 0.23 * len(code.split('\n')))
            }
        except SyntaxError:
            return {
                'cyclomatic_complexity': 0,
                'cognitive_complexity': 0,
                'maintainability_index': 0
            }

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity from AST"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points that increase complexity
            if isinstance(child, ast.If | ast.While | ast.For | ast.With | ast.Try | ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):  # and/or operators
                complexity += len(child.values) - 1

        return complexity

    def get_version(self) -> str:
        """Get analyzer version info"""
        versions = []

        if self.ruff_enabled:
            versions.append("ruff:enabled")
        if self.mypy_enabled:
            versions.append("mypy:enabled")

        return f"PythonAnalyzer({','.join(versions)})"
