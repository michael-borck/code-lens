"""
Batch processing service for handling multiple code submissions
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog

from codelens.analyzers import analyzer_manager
from codelens.api.schemas import AnalysisRequest, AnalysisResponse
from codelens.utils import (
    calculate_file_hash,
    detect_language_from_extension,
    generate_submission_id,
    parse_batch_files,
)

logger = structlog.get_logger()


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing"""
    parallel_processing: bool = True
    max_concurrent: int = 5
    skip_unsupported_files: bool = True
    extract_student_info: bool = True
    default_language: str = "python"

    # Student ID extraction patterns
    student_id_patterns: list[str] | None = None

    def __post_init__(self) -> None:
        if self.student_id_patterns is None:
            self.student_id_patterns = [
                r'(\d{6,12})',  # 6-12 digit student IDs
                r'([a-z]{2,3}\d{3,6})',  # Letters followed by numbers (e.g., cs123456)
                r'(\w+)_assignment',  # Username before _assignment
                r'(\w+)\.py',  # Filename without extension
            ]


@dataclass
class BatchFile:
    """Represents a file in a batch"""
    path: Path
    content: str
    language: str
    student_id: str | None = None
    student_name: str | None = None
    file_size: int = 0
    file_hash: str = ""

    def __post_init__(self) -> None:
        self.file_size = len(self.content.encode('utf-8'))
        self.file_hash = calculate_file_hash(self.content)


@dataclass
class BatchProcessingResult:
    """Result of batch processing operation"""
    success: bool
    batch_id: str
    total_files: int
    processed_files: int
    failed_files: int
    results: list[AnalysisResponse]
    processing_time: float
    errors: list[str]

    # Statistics
    average_score: float | None = None
    score_distribution: dict[str, int] | None = None


class BatchProcessor:
    """Service for processing multiple code submissions in batch"""

    def __init__(self, config: BatchProcessingConfig | None = None):
        self.config = config or BatchProcessingConfig()

    async def process_directory(
        self,
        directory_path: str,
        assignment_id: int | None = None,
        rubric_id: int | None = None,
        language: str | None = None
    ) -> BatchProcessingResult:
        """
        Process all supported files in a directory

        Args:
            directory_path: Path to directory containing student submissions
            assignment_id: Optional assignment ID
            rubric_id: Optional rubric ID for grading
            language: Optional language override

        Returns:
            BatchProcessingResult with processing results
        """
        start_time = datetime.utcnow()
        batch_id = generate_submission_id()

        try:
            # Discover files in directory
            files = await self._discover_files(directory_path, language)

            if not files:
                return BatchProcessingResult(
                    success=False,
                    batch_id=batch_id,
                    total_files=0,
                    processed_files=0,
                    failed_files=0,
                    results=[],
                    processing_time=0.0,
                    errors=["No supported files found in directory"]
                )

            logger.info("Starting batch processing",
                       batch_id=batch_id,
                       directory=directory_path,
                       file_count=len(files))

            # Process files
            results = await self._process_files(
                files=files,
                assignment_id=assignment_id,
                rubric_id=rubric_id
            )

            # Calculate statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            processed_count = len([r for r in results if r.success])
            failed_count = len(files) - processed_count

            # Calculate scores if available
            scores = [r.total_score for r in results if r.total_score is not None]
            average_score = sum(scores) / len(scores) if scores else None
            score_distribution = self._calculate_score_distribution(scores) if scores else None

            result = BatchProcessingResult(
                success=failed_count == 0,
                batch_id=batch_id,
                total_files=len(files),
                processed_files=processed_count,
                failed_files=failed_count,
                results=results,
                processing_time=processing_time,
                errors=[r.error_message for r in results if r.error_message],
                average_score=average_score,
                score_distribution=score_distribution
            )

            logger.info("Batch processing completed",
                       batch_id=batch_id,
                       processed=processed_count,
                       failed=failed_count,
                       processing_time=processing_time)

            return result

        except Exception as e:
            logger.error("Batch processing failed",
                        batch_id=batch_id,
                        error=str(e))
            return BatchProcessingResult(
                success=False,
                batch_id=batch_id,
                total_files=0,
                processed_files=0,
                failed_files=0,
                results=[],
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                errors=[f"Batch processing failed: {str(e)}"]
            )

    async def process_files_list(
        self,
        files_data: list[dict[str, str]],
        assignment_id: int | None = None,
        rubric_id: int | None = None,
        language: str = "python"
    ) -> BatchProcessingResult:
        """
        Process a list of file data (code + metadata)

        Args:
            files_data: List of file dictionaries with code and metadata
            assignment_id: Optional assignment ID
            rubric_id: Optional rubric ID
            language: Programming language

        Returns:
            BatchProcessingResult with processing results
        """
        start_time = datetime.utcnow()
        batch_id = generate_submission_id()

        try:
            # Parse and validate file data
            parsed_files = parse_batch_files(files_data)

            if not parsed_files:
                return BatchProcessingResult(
                    success=False,
                    batch_id=batch_id,
                    total_files=0,
                    processed_files=0,
                    failed_files=0,
                    results=[],
                    processing_time=0.0,
                    errors=["No valid files provided"]
                )

            logger.info("Processing files list",
                       batch_id=batch_id,
                       file_count=len(parsed_files))

            # Convert to BatchFile objects
            batch_files = []
            for file_data in parsed_files:
                batch_file = BatchFile(
                    path=Path(file_data['path']),
                    content=file_data['code'],
                    language=file_data['language'],
                    student_id=file_data.get('student_id'),
                    student_name=file_data.get('student_name')
                )
                batch_files.append(batch_file)

            # Process files
            results = await self._process_files(
                files=batch_files,
                assignment_id=assignment_id,
                rubric_id=rubric_id
            )

            # Calculate results
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            processed_count = len([r for r in results if r.success])
            failed_count = len(batch_files) - processed_count

            return BatchProcessingResult(
                success=failed_count == 0,
                batch_id=batch_id,
                total_files=len(batch_files),
                processed_files=processed_count,
                failed_files=failed_count,
                results=results,
                processing_time=processing_time,
                errors=[r.error_message for r in results if r.error_message]
            )

        except Exception as e:
            logger.error("Files list processing failed",
                        batch_id=batch_id,
                        error=str(e))
            return BatchProcessingResult(
                success=False,
                batch_id=batch_id,
                total_files=0,
                processed_files=0,
                failed_files=0,
                results=[],
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                errors=[f"Processing failed: {str(e)}"]
            )

    async def _discover_files(
        self,
        directory_path: str,
        language_filter: str | None = None
    ) -> list[BatchFile]:
        """Discover and read all supported files in directory"""
        directory = Path(directory_path)

        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory does not exist: {directory_path}")

        files = []

        # Walk through directory structure
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                # Check if file type is supported
                detected_language = detect_language_from_extension(file_path.name)

                if not detected_language:
                    if not self.config.skip_unsupported_files:
                        logger.warning("Unsupported file type", file=str(file_path))
                    continue

                # Apply language filter if specified
                if language_filter and detected_language != language_filter:
                    continue

                try:
                    # Read file content
                    with open(file_path, encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Extract student information
                    student_id, student_name = self._extract_student_info(file_path)

                    # Create BatchFile
                    batch_file = BatchFile(
                        path=file_path,
                        content=content,
                        language=detected_language,
                        student_id=student_id,
                        student_name=student_name
                    )

                    files.append(batch_file)

                    logger.debug("Discovered file",
                               file=str(file_path),
                               language=detected_language,
                               student_id=student_id)

                except Exception as e:
                    logger.warning("Failed to read file",
                                 file=str(file_path),
                                 error=str(e))
                    continue

        return files

    def _extract_student_info(self, file_path: Path) -> tuple[str | None, str | None]:
        """Extract student ID and name from file path"""
        if not self.config.extract_student_info:
            return None, None

        # Try to extract from file path components
        path_parts = [file_path.stem] + list(file_path.parts)

        student_id = None
        student_name = None

        for part in path_parts:
            if student_id:
                break

            for pattern in self.config.student_id_patterns or []:
                match = re.search(pattern, part.lower())
                if match:
                    student_id = match.group(1)
                    # Try to extract name from the same part
                    name_match = re.search(r'([a-z]+_[a-z]+)', part.lower())
                    if name_match:
                        student_name = name_match.group(1).replace('_', ' ').title()
                    break

        return student_id, student_name

    async def _process_files(
        self,
        files: list[BatchFile],
        assignment_id: int | None = None,
        rubric_id: int | None = None
    ) -> list[AnalysisResponse]:
        """Process multiple files, optionally in parallel"""

        if self.config.parallel_processing:
            # Process files in parallel with limited concurrency
            semaphore = asyncio.Semaphore(self.config.max_concurrent)
            tasks = [
                self._process_single_file_with_semaphore(
                    semaphore, file, assignment_id, rubric_id
                )
                for file in files
            ]
            gather_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions
            processed_results: list[AnalysisResponse] = []
            for i, result in enumerate(gather_results):
                if isinstance(result, Exception):
                    logger.error("File processing failed",
                               file=str(files[i].path),
                               error=str(result))
                    # Create error response
                    error_response = AnalysisResponse(
                        success=False,
                        submission_id=generate_submission_id(),
                        error_message=f"Processing failed: {str(result)}",
                        processing_time=0.0,
                        total_score=0.0,
                        max_score=100.0
                    )
                    processed_results.append(error_response)
                elif isinstance(result, AnalysisResponse):
                    processed_results.append(result)

            return processed_results
        else:
            # Process files sequentially
            results: list[AnalysisResponse] = []
            for file in files:
                result = await self._process_single_file(file, assignment_id, rubric_id)
                results.append(result)
            return results

    async def _process_single_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        file: BatchFile,
        assignment_id: int | None,
        rubric_id: int | None
    ) -> AnalysisResponse:
        """Process a single file with semaphore for concurrency control"""
        async with semaphore:
            return await self._process_single_file(file, assignment_id, rubric_id)

    async def _process_single_file(
        self,
        file: BatchFile,
        assignment_id: int | None,
        rubric_id: int | None
    ) -> AnalysisResponse:
        """Process a single file through the analysis pipeline"""
        try:
            # Run analysis
            start_time = datetime.utcnow()

            analysis_result = await analyzer_manager.analyze_code(
                code=file.content,
                language=file.language,
                file_path=str(file.path),
                analyzer_config=None
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Convert to response format (simplified)
            from codelens.api.routes.analysis import (
                convert_analysis_issues,
                convert_metrics,
            )

            response = AnalysisResponse(
                success=analysis_result.success,
                submission_id=generate_submission_id(),
                syntax_valid=analysis_result.success,
                issues=convert_analysis_issues(analysis_result.issues),
                metrics=convert_metrics(analysis_result.metrics),
                analysis_version=analysis_result.analyzer_version,
                processing_time=processing_time,
                tools_used={"analyzer": analysis_result.analyzer_version},
                total_score=0.0,
                max_score=100.0
            )

            logger.info("Processed file",
                       file=str(file.path),
                       success=response.success,
                       processing_time=processing_time)

            return response

        except Exception as e:
            logger.error("Single file processing failed",
                        file=str(file.path),
                        error=str(e))
            return AnalysisResponse(
                success=False,
                submission_id=generate_submission_id(),
                error_message=f"Processing failed: {str(e)}",
                processing_time=0.0,
                total_score=0.0,
                max_score=100.0
            )

    def _calculate_score_distribution(self, scores: list[float]) -> dict[str, int]:
        """Calculate score distribution by grade ranges"""
        if not scores:
            return {}

        distribution = {
            "A (90-100)": 0,
            "B (80-89)": 0,
            "C (70-79)": 0,
            "D (60-69)": 0,
            "F (0-59)": 0
        }

        for score in scores:
            if score >= 90:
                distribution["A (90-100)"] += 1
            elif score >= 80:
                distribution["B (80-89)"] += 1
            elif score >= 70:
                distribution["C (70-79)"] += 1
            elif score >= 60:
                distribution["D (60-69)"] += 1
            else:
                distribution["F (0-59)"] += 1

        return distribution


# Global batch processor instance
batch_processor = BatchProcessor()
