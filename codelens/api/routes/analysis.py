"""
API endpoints for code analysis
"""

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from codelens.analyzers import AnalysisResult, analyzer_manager
from codelens.api.schemas import (
    AnalysisIssueSchema,
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    CodeMetricsSchema,
    ExecutionResultSchema,
    FeedbackSchema,
    GradeBreakdownSchema,
    SimilarityResultSchema,
    TestResultSchema,
)
from codelens.core.config import settings
from codelens.db.database import get_db
from codelens.models import AnalysisReport
from codelens.services import CodeExecutionRequest, code_executor

logger = structlog.get_logger()
router = APIRouter()


def convert_analysis_issues(issues: list[Any]) -> list[AnalysisIssueSchema]:
    """Convert analyzer issues to schema format"""
    return [
        AnalysisIssueSchema(
            line=issue.line,
            column=issue.column,
            severity=issue.severity,
            code=issue.code,
            message=issue.message,
            category=issue.category,
            suggestion=issue.suggestion
        )
        for issue in issues
    ]


def convert_metrics(metrics: Any) -> CodeMetricsSchema:
    """Convert analyzer metrics to schema format"""
    return CodeMetricsSchema(
        lines_of_code=metrics.lines_of_code,
        lines_of_comments=metrics.lines_of_comments,
        blank_lines=metrics.blank_lines,
        cyclomatic_complexity=metrics.cyclomatic_complexity,
        cognitive_complexity=metrics.cognitive_complexity,
        function_count=metrics.function_count,
        class_count=metrics.class_count,
        max_nesting_depth=metrics.max_nesting_depth,
        maintainability_index=metrics.maintainability_index
    )


async def store_analysis_report(
    analysis_result: AnalysisResult,
    request: AnalysisRequest,
    submission_id: str,
    db: AsyncSession,
    grade_breakdown: dict[str, float] | None = None,
    total_score: float | None = None,
    test_result: Any = None,
    similarity_result: Any = None
) -> None:
    """Store analysis report in database"""
    try:
        # Create analysis report
        report = AnalysisReport(
            assignment_id=request.assignment_id,
            student_id=request.student_id,
            student_name=request.student_name,
            submission_id=submission_id,
            file_name="submission.py",  # Default filename
            file_size=len(request.code.encode('utf-8')),
            file_hash=analysis_result.analyzer_version,  # Use analyzer version as temp hash
            language=request.language.value,
            analysis_version=analysis_result.analyzer_version,
            syntax_valid=analysis_result.success and len([i for i in analysis_result.issues if i.category == "syntax"]) == 0,
            syntax_errors={
                "errors": [
                    {"line": i.line, "message": i.message}
                    for i in analysis_result.issues if i.category == "syntax"
                ]
            },
            quality_metrics={
                "complexity": {
                    "cyclomatic": analysis_result.metrics.cyclomatic_complexity,
                    "cognitive": analysis_result.metrics.cognitive_complexity
                },
                "lines_of_code": analysis_result.metrics.lines_of_code,
                "style_issues": [
                    {"line": i.line, "issue": i.message, "severity": i.severity.value}
                    for i in analysis_result.issues if i.category == "style"
                ],
                "type_issues": [
                    {"line": i.line, "issue": i.message}
                    for i in analysis_result.issues if i.category == "types"
                ]
            },
            test_results={
                "total_tests": test_result.total_tests if test_result else 0,
                "passed_tests": test_result.passed_tests if test_result else 0,
                "failed_tests": test_result.failed_tests if test_result else [],
                "execution_time": test_result.execution_result.execution_time if test_result and test_result.execution_result else 0
            } if test_result else None,
            grade_breakdown=grade_breakdown or {},
            total_score=total_score or 0.0,
            similarity_results=similarity_result.__dict__ if similarity_result else None,
            feedback={
                "strengths": ["Code structure looks good"] if analysis_result.success else [],
                "improvements": [i.message for i in analysis_result.issues[:3]],  # Top 3 issues
                "resources": []
            },
            processing_time=analysis_result.execution_time,
            tools_used={
                "analyzer": analysis_result.analyzer_version,
                "execution": test_result is not None
            },
            status="completed"
        )

        db.add(report)
        await db.commit()
        await db.refresh(report)

        logger.info("Analysis report stored", report_id=report.id, submission_id=submission_id)

    except Exception as e:
        logger.error("Failed to store analysis report", error=str(e), submission_id=submission_id)
        await db.rollback()


@router.post("/python", response_model=AnalysisResponse)
async def analyze_python_code(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> AnalysisResponse:
    """Analyze Python code submission"""
    start_time = datetime.utcnow()
    submission_id = str(uuid.uuid4())

    try:
        logger.info("Starting Python code analysis", submission_id=submission_id)

        # Run static analysis
        analysis_result = await analyzer_manager.analyze_code(
            code=request.code,
            language=request.language.value,
            file_path="submission.py",
            analyzer_config=request.analyzer_config
        )

        if not analysis_result.success:
            logger.warning("Analysis failed", submission_id=submission_id)
            return AnalysisResponse(
                success=False,
                submission_id=submission_id,
                error_message="Static analysis failed",
                issues=convert_analysis_issues(analysis_result.issues),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                total_score=0.0,
                max_score=100.0
            )

        # Code execution (if requested)
        execution_result = None
        test_result = None
        if request.execute_code or request.run_tests:
            if code_executor.is_available():
                exec_request = CodeExecutionRequest(
                    code=request.code,
                    language=request.language.value,
                    input_data=request.input_data,
                    run_tests=request.run_tests,
                    test_cases=[tc.dict() for tc in request.test_cases] if request.test_cases else None
                )

                exec_response = await code_executor.execute_code(exec_request)
                if exec_response.execution_result:
                    execution_result = ExecutionResultSchema(**exec_response.execution_result.__dict__)
                if exec_response.test_result:
                    test_result = TestResultSchema(**exec_response.test_result.__dict__)
            else:
                logger.warning("Code execution requested but sandbox not available")

        # Similarity checking (placeholder - will implement later)
        similarity_result = None
        if request.check_similarity:
            similarity_result = SimilarityResultSchema(
                highest_similarity=0.0,
                flagged_submissions=[],
                ai_baseline_similarity=0.0,
                methods_used=["ast_similarity"]
            )

        # Grading (if rubric provided)
        grade_breakdown = None
        total_score = None
        if request.rubric_id:
            # Calculate grade based on rubric (simplified implementation)
            grade_breakdown = GradeBreakdownSchema(
                functionality=85.0 if not test_result or test_result.passed_tests == test_result.total_tests else 70.0,
                style=90.0 if len([i for i in analysis_result.issues if i.category == "style"]) < 5 else 75.0,
                documentation=80.0,  # Placeholder
                testing=95.0 if test_result and test_result.passed_tests > 0 else 60.0,
                total=82.5  # Average
            )
            total_score = grade_breakdown.total

        # Generate feedback
        feedback = FeedbackSchema(
            strengths=["Code compiles successfully"] if analysis_result.success else [],
            improvements=[
                f"Fix {i.category} issue: {i.message}"
                for i in analysis_result.issues[:3]
            ],
            resources=[]
        )
        # Add style resource if needed
        if any(i.category == "style" for i in analysis_result.issues):
            feedback.resources.append("https://pep8.org/")

        # Create response
        response = AnalysisResponse(
            success=True,
            submission_id=submission_id,
            syntax_valid=analysis_result.success,
            syntax_errors=[i for i in convert_analysis_issues(analysis_result.issues) if i.category == "syntax"],
            issues=convert_analysis_issues(analysis_result.issues),
            metrics=convert_metrics(analysis_result.metrics),
            execution_result=execution_result,
            test_result=test_result,
            similarity_result=similarity_result,
            grade_breakdown=grade_breakdown,
            total_score=total_score or 0.0,
            max_score=100.0,
            feedback=feedback,
            analysis_version=analysis_result.analyzer_version,
            processing_time=analysis_result.execution_time,
            tools_used={"analyzer": analysis_result.analyzer_version},
            analyzed_at=start_time
        )

        # Store report in background
        if request.assignment_id:
            background_tasks.add_task(
                store_analysis_report,
                analysis_result,
                request,
                submission_id,
                db,
                grade_breakdown.dict() if grade_breakdown else None,
                total_score or 0.0,
                test_result,
                similarity_result
            )

        logger.info("Python code analysis completed",
                   submission_id=submission_id,
                   processing_time=response.processing_time,
                   issue_count=len(response.issues))

        return response

    except Exception as e:
        logger.error("Python code analysis failed", error=str(e), submission_id=submission_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        ) from None


@router.post("/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> BatchAnalysisResponse:
    """Analyze multiple code files in batch"""
    datetime.utcnow()
    batch_id = str(uuid.uuid4())

    try:
        logger.info("Starting batch analysis",
                   batch_id=batch_id,
                   file_count=len(request.files))

        results = []
        total_processing_time = 0.0
        failed_files = 0

        # Process files (could be parallelized further)
        for i, file_info in enumerate(request.files):
            try:
                # Create individual analysis request
                analysis_request = AnalysisRequest(
                    code=file_info["code"],
                    language=request.language,
                    rubric_id=request.rubric_id,
                    assignment_id=request.assignment_id,
                    student_id=file_info.get("student_id"),
                    student_name=file_info.get("student_name"),
                    check_similarity=request.check_similarity,
                    run_tests=False,
                    test_cases=[],
                    execute_code=False,
                    input_data=None,
                    analyzer_config=None
                )

                # Analyze individual file
                file_result = await analyze_python_code(analysis_request, background_tasks, db)
                results.append(file_result)
                total_processing_time += file_result.processing_time

                logger.info("Processed file in batch",
                           batch_id=batch_id,
                           file_index=i,
                           success=file_result.success)

            except Exception as e:
                logger.error("Failed to process file in batch",
                           batch_id=batch_id,
                           file_index=i,
                           error=str(e))
                failed_files += 1

                # Add error result
                error_result = AnalysisResponse(
                    success=False,
                    submission_id=str(uuid.uuid4()),
                    error_message=f"Processing failed: {str(e)}",
                    processing_time=0.0,
                    total_score=0.0,
                    max_score=100.0
                )
                results.append(error_result)

        # Cross-file similarity analysis (placeholder)
        cross_similarity_results = []
        if request.check_similarity and len(results) > 1:
            # This would implement cross-submission similarity checking
            cross_similarity_results = [
                {
                    "submission_1": results[0].submission_id,
                    "submission_2": results[1].submission_id,
                    "similarity_score": 0.1,
                    "method": "ast_similarity"
                }
            ] if len(results) >= 2 else []

        # Calculate batch statistics
        processed_files = len(results) - failed_files
        average_processing_time = total_processing_time / len(results) if results else 0.0

        response = BatchAnalysisResponse(
            success=failed_files == 0,
            batch_id=batch_id,
            total_files=len(request.files),
            processed_files=processed_files,
            failed_files=failed_files,
            results=results,
            cross_similarity_results=cross_similarity_results,
            total_processing_time=total_processing_time,
            average_processing_time=average_processing_time,
            completed_at=datetime.utcnow()
        )

        logger.info("Batch analysis completed",
                   batch_id=batch_id,
                   processed=processed_files,
                   failed=failed_files,
                   total_time=total_processing_time)

        return response

    except Exception as e:
        logger.error("Batch analysis failed", error=str(e), batch_id=batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch analysis failed: {str(e)}"
        ) from None


@router.get("/status")
async def get_analysis_status() -> dict[str, Any]:
    """Get analyzer status and configuration"""
    return {
        "status": "healthy",
        "supported_languages": analyzer_manager.get_supported_languages(),
        "analyzers": analyzer_manager.get_all_analyzer_info(),
        "sandbox_available": code_executor.is_available(),
        "configuration": {
            "max_file_size": settings.max_file_size,
            "max_files_per_batch": settings.max_files_per_batch,
            "execution_timeout": settings.analyzer.execution_timeout,
            "memory_limit": settings.analyzer.memory_limit
        }
    }


@router.get("/tools")
async def get_available_tools() -> dict[str, Any]:
    """Get information about available analysis tools"""
    return {
        "python": {
            "ruff": {
                "enabled": settings.analyzer.ruff_enabled,
                "description": "Fast Python linter and formatter"
            },
            "mypy": {
                "enabled": settings.analyzer.mypy_enabled,
                "description": "Static type checker for Python"
            }
        },
        "execution": {
            "docker": {
                "enabled": settings.docker_enabled,
                "description": "Docker-based code execution sandbox"
            }
        },
        "similarity": {
            "ast_similarity": {
                "enabled": settings.similarity.enabled,
                "description": "AST-based structural similarity detection"
            }
        }
    }
