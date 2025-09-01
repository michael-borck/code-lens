"""
Database models for rubrics and grading criteria
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from codelens.db.database import Base

if TYPE_CHECKING:
    from .assignments import Assignment


class Rubric(Base):
    """Rubric for grading assignments"""

    __tablename__ = "rubrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Rubric configuration
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False)  # Grading criteria
    weights: Mapped[dict] = mapped_column(JSON, nullable=False)   # Category weights
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Analysis configuration
    analysis_config: Mapped[dict] = mapped_column(JSON, nullable=True)  # Tool configs

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
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment", back_populates="rubric", cascade="all, delete-orphan"
    )


class RubricCriterion(Base):
    """Individual criterion within a rubric"""

    __tablename__ = "rubric_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rubric_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Criterion details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # functionality, style, etc
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Auto-grading configuration
    auto_gradable: Mapped[bool] = mapped_column(nullable=False, default=True)
    evaluation_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # test_count, complexity, etc
    evaluation_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Performance levels (excellent, good, satisfactory, needs_improvement)
    performance_levels: Mapped[dict] = mapped_column(JSON, nullable=False)
