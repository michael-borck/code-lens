"""
Secure code execution sandbox using Docker containers
"""

import asyncio
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import docker  # type: ignore[import-untyped]
import structlog
from docker.errors import ContainerError, DockerException, ImageNotFound  # type: ignore[import-untyped]

from codelens.core.config import settings

logger = structlog.get_logger()


@dataclass
class ExecutionResult:
    """Result of code execution in sandbox"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    memory_used: str | None = None
    timed_out: bool = False
    error_message: str | None = None


@dataclass
class TestResult:
    """Result of running tests against code"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: list[dict[str, Any]] | None = None
    test_output: str = ""
    execution_result: ExecutionResult | None = None

    def __post_init__(self) -> None:
        if self.failed_tests is None:
            self.failed_tests = []


class DockerSandbox:
    """Docker-based sandbox for secure code execution"""

    def __init__(self) -> None:
        self.client: docker.DockerClient | None = None
        self.image_name = settings.docker_image
        self.timeout = settings.analyzer.execution_timeout
        self.memory_limit = settings.analyzer.memory_limit
        self.cpu_limit = settings.analyzer.cpu_limit

        # Initialize Docker client
        try:
            self.client = docker.from_env()
            self._ensure_image_available()
        except DockerException as e:
            logger.error("Failed to initialize Docker client", error=str(e))

    def _ensure_image_available(self) -> None:
        """Ensure the required Docker image is available"""
        if not self.client:
            return

        try:
            self.client.images.get(self.image_name)
            logger.info("Docker image available", image=self.image_name)
        except ImageNotFound:
            logger.info("Pulling Docker image", image=self.image_name)
            try:
                self.client.images.pull(self.image_name)
                logger.info("Docker image pulled successfully", image=self.image_name)
            except DockerException as e:
                logger.error("Failed to pull Docker image", image=self.image_name, error=str(e))

    async def execute_python_code(
        self,
        code: str,
        input_data: str | None = None,
        working_dir: str | None = None
    ) -> ExecutionResult:
        """
        Execute Python code in a secure sandbox

        Args:
            code: Python code to execute
            input_data: Optional stdin input for the code
            working_dir: Optional working directory for execution

        Returns:
            ExecutionResult with execution details
        """
        if not self.client:
            return ExecutionResult(
                success=False,
                error_message="Docker client not available"
            )

        start_time = time.time()

        # Create temporary directory for code files
        with tempfile.TemporaryDirectory() as temp_dir:
            code_file = Path(temp_dir) / "code.py"
            code_file.write_text(code)

            # Create input file if provided
            input_file = None
            if input_data:
                input_file = Path(temp_dir) / "input.txt"
                input_file.write_text(input_data)

            # Run code in Docker container
            return await self._run_container(
                command=["python", "/workspace/code.py"],
                volumes={temp_dir: {"bind": "/workspace", "mode": "ro"}},
                working_dir=working_dir or "/workspace",
                input_file="/workspace/input.txt" if input_file else None,
                start_time=start_time
            )

    async def run_python_tests(
        self,
        code: str,
        test_code: str,
        test_framework: str = "pytest"
    ) -> TestResult:
        """
        Run tests against Python code

        Args:
            code: Student's Python code
            test_code: Test code to run
            test_framework: Testing framework to use (pytest, unittest)

        Returns:
            TestResult with test execution details
        """
        if not self.client:
            return TestResult(
                test_output="Docker client not available",
                execution_result=ExecutionResult(
                    success=False,
                    error_message="Docker client not available"
                )
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Write code and test files
            code_file = Path(temp_dir) / "code.py"
            test_file = Path(temp_dir) / "test_code.py"

            code_file.write_text(code)
            test_file.write_text(test_code)

            # Create requirements file for test dependencies
            requirements = Path(temp_dir) / "requirements.txt"
            if test_framework == "pytest":
                requirements.write_text("pytest>=7.0.0\n")
                test_command = ["python", "-m", "pytest", "/workspace/test_code.py", "-v", "--tb=short", "--json-report", "--json-report-file=/workspace/report.json"]
            else:
                # unittest (built-in, no extra requirements)
                requirements.write_text("")
                test_command = ["python", "-m", "unittest", "/workspace/test_code.py", "-v"]

            # Install dependencies and run tests
            setup_command = """
            cd /workspace &&
            pip install --no-cache-dir -r requirements.txt &&
            """ + " ".join(test_command)

            start_time = time.time()
            execution_result = await self._run_container(
                command=["bash", "-c", setup_command],
                volumes={temp_dir: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                start_time=start_time
            )

            # Parse test results
            return await self._parse_test_results(temp_dir, test_framework, execution_result)

    async def _run_container(
        self,
        command: list[str],
        volumes: dict[str, dict[str, str]],
        working_dir: str = "/workspace",
        input_file: str | None = None,
        start_time: float | None = None
    ) -> ExecutionResult:
        """Run a command in a Docker container with security constraints"""
        if start_time is None:
            start_time = time.time()

        try:
            # Container configuration with security limits
            container_config = {
                "image": self.image_name,
                "command": command,
                "volumes": volumes,
                "working_dir": working_dir,
                "mem_limit": self.memory_limit,
                "memswap_limit": self.memory_limit,  # Disable swap
                "cpu_period": 100000,  # 100ms
                "cpu_quota": int(50000 * float(self.cpu_limit)),  # CPU limit
                "network_disabled": True,  # No network access
                "read_only": False,  # Some operations need write access
                "remove": True,  # Auto-remove container
                "stdout": True,
                "stderr": True,
                "stdin": bool(input_file),
                "tty": False,
                "user": "1000:1000",  # Non-root user
                # Security options
                "security_opt": ["no-new-privileges:true"],
                "cap_drop": ["ALL"],  # Drop all capabilities
                "tmpfs": {"/tmp": "noexec,nosuid,size=100m"},
            }

            # Run container
            if not self.client:
                raise RuntimeError("Docker client not available")
            container = self.client.containers.run(**container_config, detach=True)

            # Wait for completion with timeout
            try:
                exit_code = container.wait(timeout=self.timeout)["StatusCode"]

                # Get output
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

                execution_time = time.time() - start_time

                # Get memory stats if possible
                memory_used = None
                try:
                    stats = container.stats(stream=False)
                    memory_used = f"{stats['memory_stats'].get('usage', 0) / 1024 / 1024:.1f}MB"
                except Exception:
                    pass

                return ExecutionResult(
                    success=(exit_code == 0),
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    memory_used=memory_used,
                    timed_out=False
                )

            except asyncio.TimeoutError:
                # Container timed out
                try:
                    container.kill()
                except Exception:
                    pass

                return ExecutionResult(
                    success=False,
                    stderr="Execution timed out",
                    exit_code=-1,
                    execution_time=self.timeout,
                    timed_out=True,
                    error_message=f"Code execution exceeded {self.timeout}s timeout"
                )

        except ContainerError as e:
            return ExecutionResult(
                success=False,
                stderr=e.stderr.decode("utf-8", errors="replace") if e.stderr else "",
                exit_code=e.exit_status,
                execution_time=time.time() - start_time,
                error_message=f"Container error: {str(e)}"
            )
        except DockerException as e:
            return ExecutionResult(
                success=False,
                error_message=f"Docker error: {str(e)}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                execution_time=time.time() - start_time
            )

    async def _parse_test_results(
        self,
        temp_dir: str,
        test_framework: str,
        execution_result: ExecutionResult
    ) -> TestResult:
        """Parse test results from execution output"""
        test_result = TestResult(execution_result=execution_result)

        if test_framework == "pytest":
            # Try to parse JSON report
            report_file = Path(temp_dir) / "report.json"
            if report_file.exists():
                try:
                    with open(report_file) as f:
                        report_data = json.load(f)

                    test_result.total_tests = report_data.get("summary", {}).get("total", 0)
                    test_result.passed_tests = report_data.get("summary", {}).get("passed", 0)

                    # Parse failed tests
                    if test_result.failed_tests is None:
                        test_result.failed_tests = []
                    for test in report_data.get("tests", []):
                        if test.get("outcome") == "failed":
                            test_result.failed_tests.append({
                                "name": test.get("nodeid", "unknown"),
                                "message": test.get("call", {}).get("longrepr", ""),
                                "output": test.get("setup", {}).get("stdout", "")
                            })

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Failed to parse pytest JSON report", error=str(e))

            # Fallback to parsing stdout
            if test_result.total_tests == 0:
                self._parse_pytest_stdout(execution_result.stdout, test_result)

        else:  # unittest
            self._parse_unittest_output(execution_result.stdout, test_result)

        test_result.test_output = execution_result.stdout
        return test_result

    def _parse_pytest_stdout(self, output: str, test_result: TestResult) -> None:
        """Parse pytest stdout output for test counts"""
        lines = output.split('\n')
        for line in lines:
            if "failed" in line and "passed" in line:
                # Example: "2 failed, 3 passed in 0.12s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed" and i > 0:
                        test_result.total_tests += int(parts[i-1])
                    elif part == "passed" and i > 0:
                        test_result.passed_tests = int(parts[i-1])
                        test_result.total_tests += test_result.passed_tests

    def _parse_unittest_output(self, output: str, test_result: TestResult) -> None:
        """Parse unittest output for test counts"""
        lines = output.split('\n')
        for line in lines:
            if line.startswith("Ran ") and "test" in line:
                # Example: "Ran 5 tests in 0.001s"
                parts = line.split()
                if len(parts) >= 2:
                    test_result.total_tests = int(parts[1])
            elif "FAILED" in line and "failures=" in line:
                # Parse failure count
                for part in line.split(","):
                    if "failures=" in part:
                        failures = int(part.split("=")[1])
                        test_result.passed_tests = test_result.total_tests - failures

    def is_available(self) -> bool:
        """Check if Docker sandbox is available"""
        return self.client is not None


# Global sandbox instance
sandbox = DockerSandbox() if settings.docker_enabled else None
