"""
API endpoints for analysis reports and results
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from codelens.db.database import get_db
from codelens.models import AnalysisReport, Assignment, SimilarityMatch

logger = structlog.get_logger()
router = APIRouter()


class ReportSummary(BaseModel):
    """Summary schema for analysis reports"""
    id: int
    submission_id: str
    assignment_id: int | None = None
    student_id: str | None = None
    student_name: str | None = None
    file_name: str
    language: str
    total_score: float
    max_score: float
    syntax_valid: bool
    analyzed_at: datetime
    status: str

    class Config:
        from_attributes = True


class ReportDetail(BaseModel):
    """Detailed schema for analysis reports"""
    id: int
    submission_id: str
    assignment_id: int | None = None
    student_id: str | None = None
    student_name: str | None = None
    file_name: str
    file_size: int
    file_hash: str
    language: str
    analysis_version: str

    # Analysis results
    syntax_valid: bool
    syntax_errors: dict[str, Any] | None = None
    quality_metrics: dict[str, Any]
    test_results: dict[str, Any] | None = None
    grade_breakdown: dict[str, Any]
    total_score: float
    max_score: float
    similarity_results: dict[str, Any] | None = None
    feedback: dict[str, Any]

    # Metadata
    processing_time: float
    tools_used: dict[str, Any]
    status: str
    analyzed_at: datetime

    class Config:
        from_attributes = True


class SimilarityMatchResponse(BaseModel):
    """Schema for similarity match results"""
    id: int
    report_id: int
    matched_report_id: int
    similarity_score: float
    similarity_method: str
    matched_sections: dict[str, Any]
    confidence: float
    flagged: bool
    reviewed: bool
    review_decision: str | None = None
    reviewer_notes: str | None = None
    detected_at: datetime

    class Config:
        from_attributes = True


class AssignmentStatistics(BaseModel):
    """Statistics for an assignment"""
    assignment_id: int
    total_submissions: int
    average_score: float
    median_score: float
    score_distribution: dict[str, int]  # Grade ranges
    common_issues: list[dict[str, Any]]
    completion_rate: float
    similarity_flags: int


@router.get("/", response_model=list[ReportSummary])
async def list_reports(
    assignment_id: int | None = None,
    student_id: str | None = None,
    language: str | None = None,
    status: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List analysis reports with filtering options"""
    try:
        query = select(AnalysisReport)

        # Apply filters
        if assignment_id:
            query = query.where(AnalysisReport.assignment_id == assignment_id)
        if student_id:
            query = query.where(AnalysisReport.student_id == student_id)
        if language:
            query = query.where(AnalysisReport.language == language.lower())
        if status:
            query = query.where(AnalysisReport.status == status)

        # Order by most recent first
        query = query.order_by(desc(AnalysisReport.analyzed_at))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        reports = result.scalars().all()

        logger.info("Listed analysis reports",
                   count=len(reports),
                   assignment_id=assignment_id,
                   student_id=student_id)

        return [ReportSummary.model_validate(report) for report in reports]

    except Exception as e:
        logger.error("Failed to list reports", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reports: {str(e)}"
        ) from None


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed analysis report by ID"""
    try:
        result = await db.execute(
            select(AnalysisReport).where(AnalysisReport.id == report_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            ) from None

        logger.info("Retrieved analysis report", report_id=report_id)

        return ReportDetail.model_validate(report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report", report_id=report_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report: {str(e)}"
        ) from None


@router.get("/submission/{submission_id}", response_model=ReportDetail)
async def get_report_by_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get analysis report by submission ID"""
    try:
        result = await db.execute(
            select(AnalysisReport).where(AnalysisReport.submission_id == submission_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report for submission {submission_id} not found"
            ) from None

        logger.info("Retrieved report by submission", submission_id=submission_id)

        return ReportDetail.model_validate(report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report by submission",
                   submission_id=submission_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report: {str(e)}"
        ) from None


@router.get("/assignment/{assignment_id}/statistics", response_model=AssignmentStatistics)
async def get_assignment_statistics(
    assignment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for an assignment"""
    try:
        # Verify assignment exists
        assignment_result = await db.execute(
            select(Assignment).where(Assignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment {assignment_id} not found"
            ) from None

        # Get all reports for the assignment
        reports_result = await db.execute(
            select(AnalysisReport).where(AnalysisReport.assignment_id == assignment_id)
        )
        reports = reports_result.scalars().all()

        if not reports:
            return AssignmentStatistics(
                assignment_id=assignment_id,
                total_submissions=0,
                average_score=0.0,
                median_score=0.0,
                score_distribution={},
                common_issues=[],
                completion_rate=0.0,
                similarity_flags=0
            )

        # Calculate statistics
        scores = [report.total_score for report in reports]
        total_submissions = len(reports)
        average_score = sum(scores) / total_submissions

        # Median score
        sorted_scores = sorted(scores)
        median_score = (
            sorted_scores[total_submissions // 2] if total_submissions % 2 == 1
            else (sorted_scores[total_submissions // 2 - 1] + sorted_scores[total_submissions // 2]) / 2
        )

        # Score distribution
        score_distribution = {
            "A (90-100)": len([s for s in scores if s >= 90]),
            "B (80-89)": len([s for s in scores if 80 <= s < 90]),
            "C (70-79)": len([s for s in scores if 70 <= s < 80]),
            "D (60-69)": len([s for s in scores if 60 <= s < 70]),
            "F (0-59)": len([s for s in scores if s < 60])
        }

        # Common issues (simplified - would need more sophisticated analysis)
        common_issues = [
            {"issue": "Style violations", "count": len([r for r in reports if r.quality_metrics.get("style_issues", [])])},
            {"issue": "Type errors", "count": len([r for r in reports if r.quality_metrics.get("type_issues", [])])},
            {"issue": "High complexity", "count": len([r for r in reports if r.quality_metrics.get("complexity", {}).get("cyclomatic", 0) > 10])}
        ]

        # Completion rate (submissions with tests passing)
        completed = len([r for r in reports if r.test_results and r.test_results.get("passed_tests", 0) > 0])
        completion_rate = (completed / total_submissions) * 100 if total_submissions > 0 else 0

        # Similarity flags
        similarity_flags_result = await db.execute(
            select(func.count(SimilarityMatch.id)).where(
                and_(
                    SimilarityMatch.report_id.in_([r.id for r in reports]),
                    SimilarityMatch.flagged
                )
            )
        )
        similarity_flags = similarity_flags_result.scalar() or 0

        statistics = AssignmentStatistics(
            assignment_id=assignment_id,
            total_submissions=total_submissions,
            average_score=average_score,
            median_score=median_score,
            score_distribution=score_distribution,
            common_issues=common_issues,
            completion_rate=completion_rate,
            similarity_flags=similarity_flags
        )

        logger.info("Generated assignment statistics",
                   assignment_id=assignment_id,
                   total_submissions=total_submissions)

        return statistics

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get assignment statistics",
                   assignment_id=assignment_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assignment statistics: {str(e)}"
        ) from None


@router.get("/student/{student_id}", response_model=list[ReportSummary])
async def get_student_reports(
    student_id: str,
    assignment_id: int | None = None,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get all reports for a specific student"""
    try:
        query = select(AnalysisReport).where(AnalysisReport.student_id == student_id)

        if assignment_id:
            query = query.where(AnalysisReport.assignment_id == assignment_id)

        query = query.order_by(desc(AnalysisReport.analyzed_at))
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        reports = result.scalars().all()

        logger.info("Retrieved student reports",
                   student_id=student_id,
                   count=len(reports))

        return [ReportSummary.model_validate(report) for report in reports]

    except Exception as e:
        logger.error("Failed to get student reports",
                   student_id=student_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get student reports: {str(e)}"
        ) from None


@router.get("/similarity/{report_id}", response_model=list[SimilarityMatchResponse])
async def get_similarity_matches(
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get similarity matches for a specific report"""
    try:
        # Verify report exists
        report_result = await db.execute(
            select(AnalysisReport).where(AnalysisReport.id == report_id)
        )
        report = report_result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            ) from None

        # Get similarity matches
        matches_result = await db.execute(
            select(SimilarityMatch).where(
                SimilarityMatch.report_id == report_id
            ).order_by(desc(SimilarityMatch.similarity_score))
        )
        matches = matches_result.scalars().all()

        logger.info("Retrieved similarity matches",
                   report_id=report_id,
                   match_count=len(matches))

        return [SimilarityMatchResponse.model_validate(match) for match in matches]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get similarity matches",
                   report_id=report_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get similarity matches: {str(e)}"
        ) from None


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an analysis report"""
    try:
        result = await db.execute(
            select(AnalysisReport).where(AnalysisReport.id == report_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            ) from None

        await db.delete(report)
        await db.commit()

        logger.info("Deleted analysis report", report_id=report_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete report", report_id=report_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {str(e)}"
        ) from None
