"""
Database models for analysis reports and results
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from codelens.db.database import Base

if TYPE_CHECKING:
    from .assignments import Assignment


class AnalysisReport(Base):
    """Analysis report for a code submission (metadata only, not the code itself)"""

    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Assignment and student information
    assignment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assignments.id"), nullable=False, index=True
    )
    student_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    student_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submission_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Unique submission ID

    # File information (metadata only)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 hash
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    # Analysis results
    analysis_version: Mapped[str] = mapped_column(String(20), nullable=False)  # Version of analysis tools

    # Syntax and validation results
    syntax_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    syntax_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Code quality metrics
    quality_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Expected structure: {
    #   "complexity": {"cyclomatic": 5, "cognitive": 8},
    #   "lines_of_code": 120,
    #   "style_issues": [...],
    #   "type_issues": [...],
    #   "documentation_score": 0.75
    # }

    # Test execution results
    test_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Expected structure: {
    #   "total_tests": 10,
    #   "passed_tests": 8,
    #   "failed_tests": [...],
    #   "execution_time": 1.23,
    #   "memory_usage": "45MB"
    # }

    # Grading results
    grade_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Expected structure: {
    #   "functionality": 85,
    #   "style": 90,
    #   "documentation": 70,
    #   "testing": 95,
    #   "total": 85
    # }
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)

    # Similarity analysis
    similarity_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Expected structure: {
    #   "highest_similarity": 0.15,
    #   "flagged_submissions": [...],
    #   "ai_baseline_similarity": 0.45,
    #   "methods_used": ["ast_similarity", "token_similarity"]
    # }

    # Feedback and recommendations
    feedback: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Expected structure: {
    #   "strengths": [...],
    #   "improvements": [...],
    #   "resources": [...],
    #   "detailed_comments": {...}
    # }

    # Processing metadata
    processing_time: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    tools_used: Mapped[dict] = mapped_column(JSON, nullable=False)  # Which analysis tools were used

    # Status and timestamps
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")  # pending, processing, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="reports")
    similarity_matches: Mapped[list["SimilarityMatch"]] = relationship(
        "SimilarityMatch",
        foreign_keys="SimilarityMatch.report_id",
        back_populates="report",
        cascade="all, delete-orphan"
    )


class SimilarityMatch(Base):
    """Records of similarity matches between submissions"""

    __tablename__ = "similarity_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Source and target reports
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_reports.id"), nullable=False, index=True
    )
    matched_report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_reports.id"), nullable=False, index=True
    )

    # Similarity metrics
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_method: Mapped[str] = mapped_column(String(50), nullable=False)  # ast, token, etc

    # Match details
    matched_sections: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Expected structure: {
    #   "functions": [...],
    #   "code_blocks": [...],
    #   "variable_patterns": [...]
    # }

    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Review status
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)  # flagged, cleared, escalated
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    report: Mapped["AnalysisReport"] = relationship(
        "AnalysisReport",
        foreign_keys=[report_id],
        back_populates="similarity_matches"
    )
    matched_report: Mapped["AnalysisReport"] = relationship(
        "AnalysisReport",
        foreign_keys=[matched_report_id]
    )
