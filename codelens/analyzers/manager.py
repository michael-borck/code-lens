"""
Analyzer manager for orchestrating different code analyzers
"""

from typing import Any

import structlog

from codelens.core.config import settings

from .base import AnalysisIssue, AnalysisResult, BaseAnalyzer, CodeMetrics, Severity
from .python_analyzer import PythonAnalyzer

logger = structlog.get_logger()


class AnalyzerManager:
    """Manages and orchestrates different code analyzers"""

    def __init__(self):
        self.analyzers: dict[str, BaseAnalyzer] = {}
        self._initialize_analyzers()

    def _initialize_analyzers(self) -> None:
        """Initialize available analyzers based on configuration"""

        # Python analyzer
        python_config = {
            "ruff_enabled": settings.analyzer.ruff_enabled,
            "mypy_enabled": settings.analyzer.mypy_enabled,
            "ruff_config": settings.analyzer.ruff_config,
            "mypy_config": settings.analyzer.mypy_config,
            "max_line_length": settings.analyzer.max_line_length,
            "check_type_hints": settings.analyzer.check_type_hints,
            "check_docstrings": settings.analyzer.check_docstrings,
        }
        self.analyzers["python"] = PythonAnalyzer(python_config)

        logger.info("Initialized analyzers", analyzers=list(self.analyzers.keys()))

    async def analyze_code(
        self,
        code: str,
        language: str,
        file_path: str = "temp",
        analyzer_config: dict[str, Any] | None = None
    ) -> AnalysisResult:
        """
        Analyze code using the appropriate analyzer for the language

        Args:
            code: Source code to analyze
            language: Programming language (python, javascript, etc.)
            file_path: Optional file path for context
            analyzer_config: Optional analyzer-specific configuration

        Returns:
            AnalysisResult with combined results from all applicable analyzers
        """
        language = language.lower()

        if language not in self.analyzers:
            logger.warning("Unsupported language", language=language)
            return AnalysisResult(
                success=False,
                issues=[AnalysisIssue(
                    line=1,
                    severity=Severity.ERROR,
                    code="UNSUPPORTED_LANGUAGE",
                    message=f"Language '{language}' is not supported",
                    category="system"
                )],
                metrics=CodeMetrics(),
                analyzer_version="AnalyzerManager"
            )

        # Get the appropriate analyzer
        analyzer = self.analyzers[language]

        # Override analyzer configuration if provided
        if analyzer_config:
            # Create a new analyzer instance with custom config
            if language == "python":
                analyzer = PythonAnalyzer(analyzer_config)
            # Add other language analyzers here when implemented

        try:
            logger.info("Starting code analysis", language=language, file_path=file_path)
            result = await analyzer.analyze(code, file_path)
            logger.info("Analysis completed",
                       language=language,
                       success=result.success,
                       issue_count=len(result.issues),
                       execution_time=result.execution_time)
            return result

        except Exception as e:
            logger.error("Analysis failed", language=language, error=str(e))
            return AnalysisResult(
                success=False,
                issues=[AnalysisIssue(
                    line=1,
                    severity=Severity.ERROR,
                    code="ANALYSIS_ERROR",
                    message=f"Analysis failed: {str(e)}",
                    category="system"
                )],
                metrics=CodeMetrics(),
                analyzer_version=analyzer.get_version()
            )

    async def analyze_batch(
        self,
        files: list[dict[str, str | dict[str, Any]]],
        language: str,
        analyzer_config: dict[str, Any] | None = None
    ) -> list[AnalysisResult]:
        """
        Analyze multiple files in batch

        Args:
            files: List of file dictionaries with 'code', 'path' keys
            language: Programming language
            analyzer_config: Optional analyzer configuration

        Returns:
            List of AnalysisResult objects
        """
        results = []

        for file_info in files:
            code = file_info.get("code", "")
            file_path = file_info.get("path", "unknown")

            result = await self.analyze_code(
                code=code,
                language=language,
                file_path=file_path,
                analyzer_config=analyzer_config
            )
            results.append(result)

        return results

    def get_supported_languages(self) -> list[str]:
        """Get list of supported programming languages"""
        return list(self.analyzers.keys())

    def get_analyzer_info(self, language: str) -> dict[str, Any] | None:
        """Get information about a specific analyzer"""
        if language not in self.analyzers:
            return None

        analyzer = self.analyzers[language]
        return {
            "language": language,
            "version": analyzer.get_version(),
            "name": analyzer.name,
            "config": analyzer.config
        }

    def get_all_analyzer_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all available analyzers"""
        info = {}
        for language in self.analyzers:
            info[language] = self.get_analyzer_info(language)
        return info

    def update_analyzer_config(self, language: str, config: dict[str, Any]) -> bool:
        """
        Update configuration for a specific analyzer

        Args:
            language: Programming language
            config: New configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        if language not in self.analyzers:
            logger.warning("Cannot update config for unsupported language", language=language)
            return False

        try:
            # Create new analyzer instance with updated config
            if language == "python":
                self.analyzers[language] = PythonAnalyzer(config)
            # Add other languages here

            logger.info("Updated analyzer config", language=language)
            return True

        except Exception as e:
            logger.error("Failed to update analyzer config", language=language, error=str(e))
            return False


# Global analyzer manager instance
analyzer_manager = AnalyzerManager()
