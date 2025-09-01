"""
Database models for assignments and specifications
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from codelens.db.database import Base

if TYPE_CHECKING:
    from .reports import AnalysisReport
    from .rubrics import Rubric


class Assignment(Base):
    """Assignment specification and requirements"""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Course information
    course_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    course_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    semester: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Assignment configuration
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rubric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rubrics.id"), nullable=False, index=True
    )

    # Requirements and specifications
    requirements: Mapped[dict] = mapped_column(JSON, nullable=False)  # Technical requirements
    test_cases: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Expected outputs
    starter_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Similarity checking configuration
    similarity_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    similarity_threshold: Mapped[float] = mapped_column(nullable=False, default=0.8)
    cross_cohort_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # AI baseline configuration
    ai_baselines: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Generated code variants

    # Deadlines
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    late_penalty: Mapped[float | None] = mapped_column(nullable=True, default=0.0)  # Per day penalty

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    rubric: Mapped["Rubric"] = relationship("Rubric", back_populates="assignments")
    reports: Mapped[list["AnalysisReport"]] = relationship(
        "AnalysisReport", back_populates="assignment", cascade="all, delete-orphan"
    )


class TestCase(Base):
    """Test cases for assignment validation"""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assignments.id"), nullable=False, index=True
    )

    # Test case details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String(50), nullable=False)  # unit, integration, etc

    # Test configuration
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_code: Mapped[str | None] = mapped_column(Text, nullable=True)  # Custom test code

    # Scoring
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
