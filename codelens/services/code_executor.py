"""
Service for executing student code safely with validation and testing
"""

from dataclasses import dataclass
from typing import Any

import structlog

from codelens.core.config import settings

from .sandbox import ExecutionResult, TestResult, sandbox

logger = structlog.get_logger()


@dataclass
class CodeExecutionRequest:
    """Request for code execution"""
    code: str
    language: str = "python"
    input_data: str | None = None
    timeout: int | None = None
    memory_limit: str | None = None

    # Test execution options
    run_tests: bool = False
    test_code: str | None = None
    test_cases: list[dict[str, Any]] | None = None
    test_framework: str = "pytest"


@dataclass
class ValidationResult:
    """Result of code validation"""
    is_valid: bool = True
    issues: list[str] = None
    security_risks: list[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.security_risks is None:
            self.security_risks = []


@dataclass
class CodeExecutionResponse:
    """Response from code execution"""
    success: bool
    execution_result: ExecutionResult | None = None
    test_result: TestResult | None = None
    validation_result: ValidationResult | None = None
    error_message: str | None = None


class CodeExecutorService:
    """High-level service for executing student code safely"""

    def __init__(self):
        self.sandbox = sandbox

    async def execute_code(self, request: CodeExecutionRequest) -> CodeExecutionResponse:
        """
        Execute code with optional testing

        Args:
            request: CodeExecutionRequest with code and execution parameters

        Returns:
            CodeExecutionResponse with execution results
        """
        if not self.sandbox or not self.sandbox.is_available():
            return CodeExecutionResponse(
                success=False,
                error_message="Code execution sandbox not available"
            )

        # Validate code first
        validation_result = await self._validate_code(request.code, request.language)
        if not validation_result.is_valid:
            return CodeExecutionResponse(
                success=False,
                validation_result=validation_result,
                error_message="Code validation failed"
            )

        try:
            execution_result = None
            test_result = None

            if request.language.lower() == "python":
                # Execute Python code
                if request.test_code or request.test_cases:
                    # Run with tests
                    test_result = await self._run_python_tests(request)
                else:
                    # Simple execution
                    execution_result = await self.sandbox.execute_python_code(
                        code=request.code,
                        input_data=request.input_data
                    )

            else:
                return CodeExecutionResponse(
                    success=False,
                    error_message=f"Language '{request.language}' not supported for execution"
                )

            return CodeExecutionResponse(
                success=True,
                execution_result=execution_result,
                test_result=test_result,
                validation_result=validation_result
            )

        except Exception as e:
            logger.error("Code execution failed", error=str(e))
            return CodeExecutionResponse(
                success=False,
                error_message=f"Execution failed: {str(e)}"
            )

    async def _validate_code(self, code: str, language: str) -> ValidationResult:
        """
        Validate code for security issues and basic correctness

        Args:
            code: Source code to validate
            language: Programming language

        Returns:
            ValidationResult with validation details
        """
        issues = []
        security_risks = []

        if language.lower() == "python":
            # Check for dangerous imports and operations
            dangerous_imports = [
                "os", "sys", "subprocess", "socket", "urllib", "requests",
                "http", "ftplib", "smtplib", "telnetlib", "imaplib", "nntplib",
                "email", "json", "pickle", "marshal", "shelve", "dbm",
                "sqlite3", "threading", "multiprocessing", "ctypes", "gc",
                "__import__", "eval", "exec", "compile", "globals", "locals"
            ]

            # Check for file operations
            file_operations = ["open(", "file(", "with open"]

            # Check for network operations
            network_operations = ["socket.", "urllib.", "requests.", "http."]

            # Check for system operations
            system_operations = ["os.", "sys.", "subprocess.", "system("]

            code_lower = code.lower()

            # Check dangerous imports
            for imp in dangerous_imports:
                if f"import {imp}" in code or f"from {imp}" in code:
                    security_risks.append(f"Potentially dangerous import: {imp}")

            # Check file operations
            for op in file_operations:
                if op in code_lower:
                    security_risks.append(f"File operation detected: {op}")

            # Check network operations
            for op in network_operations:
                if op in code_lower:
                    security_risks.append(f"Network operation detected: {op}")

            # Check system operations
            for op in system_operations:
                if op in code_lower:
                    security_risks.append(f"System operation detected: {op}")

            # Check for eval/exec
            if "eval(" in code or "exec(" in code:
                security_risks.append("Dynamic code execution detected (eval/exec)")

            # Check code length
            if len(code) > settings.max_file_size:
                issues.append(f"Code too large: {len(code)} bytes (max: {settings.max_file_size})")

            # Basic syntax check
            try:
                compile(code, "<string>", "exec")
            except SyntaxError as e:
                issues.append(f"Syntax error: {e}")

        else:
            issues.append(f"Validation not implemented for language: {language}")

        # Determine if validation passed
        is_valid = len(issues) == 0 and len(security_risks) == 0

        # For educational use, we might want to allow some "security risks" with warnings
        if security_risks and not issues:
            logger.warning("Code contains potential security risks", risks=security_risks)
            # You could choose to allow execution with warnings
            # is_valid = True  # Uncomment to allow risky code

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            security_risks=security_risks
        )

    async def _run_python_tests(self, request: CodeExecutionRequest) -> TestResult:
        """Run Python tests against student code"""
        if request.test_code:
            # Use provided test code
            return await self.sandbox.run_python_tests(
                code=request.code,
                test_code=request.test_code,
                test_framework=request.test_framework
            )

        elif request.test_cases:
            # Generate test code from test cases
            test_code = self._generate_test_code_from_cases(request.test_cases, request.test_framework)
            return await self.sandbox.run_python_tests(
                code=request.code,
                test_code=test_code,
                test_framework=request.test_framework
            )

        else:
            # No tests to run
            return TestResult(test_output="No tests provided")

    def _generate_test_code_from_cases(
        self,
        test_cases: list[dict[str, Any]],
        framework: str = "pytest"
    ) -> str:
        """Generate test code from test case specifications"""
        if framework == "pytest":
            return self._generate_pytest_code(test_cases)
        else:
            return self._generate_unittest_code(test_cases)

    def _generate_pytest_code(self, test_cases: list[dict[str, Any]]) -> str:
        """Generate pytest test code from test cases"""
        test_code = "import pytest\nfrom code import *\n\n"

        for i, test_case in enumerate(test_cases):
            function_name = test_case.get("function", "main")
            inputs = test_case.get("inputs", [])
            expected = test_case.get("expected", None)
            description = test_case.get("description", f"Test case {i+1}")

            test_code += f"def test_case_{i+1}():\n"
            test_code += f"    \"\"\"{description}\"\"\"\n"

            if inputs:
                input_str = ", ".join([repr(inp) for inp in inputs])
                test_code += f"    result = {function_name}({input_str})\n"
            else:
                test_code += f"    result = {function_name}()\n"

            if expected is not None:
                test_code += f"    assert result == {repr(expected)}\n"

            test_code += "\n"

        return test_code

    def _generate_unittest_code(self, test_cases: list[dict[str, Any]]) -> str:
        """Generate unittest test code from test cases"""
        test_code = "import unittest\nfrom code import *\n\n"
        test_code += "class TestCode(unittest.TestCase):\n"

        for i, test_case in enumerate(test_cases):
            function_name = test_case.get("function", "main")
            inputs = test_case.get("inputs", [])
            expected = test_case.get("expected", None)
            description = test_case.get("description", f"Test case {i+1}")

            test_code += f"    def test_case_{i+1}(self):\n"
            test_code += f"        \"\"\"{description}\"\"\"\n"

            if inputs:
                input_str = ", ".join([repr(inp) for inp in inputs])
                test_code += f"        result = {function_name}({input_str})\n"
            else:
                test_code += f"        result = {function_name}()\n"

            if expected is not None:
                test_code += f"        self.assertEqual(result, {repr(expected)})\n"

            test_code += "\n"

        test_code += "\nif __name__ == '__main__':\n"
        test_code += "    unittest.main()\n"

        return test_code

    def is_available(self) -> bool:
        """Check if code execution is available"""
        return self.sandbox and self.sandbox.is_available()


# Global code executor instance
code_executor = CodeExecutorService()
