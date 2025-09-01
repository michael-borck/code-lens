"""
API endpoints for rubric management
"""


import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codelens.api.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    RubricCreate,
    RubricResponse,
)
from codelens.db.database import get_db
from codelens.models import Assignment, Rubric

logger = structlog.get_logger()
router = APIRouter()


@router.post("/", response_model=RubricResponse, status_code=status.HTTP_201_CREATED)
async def create_rubric(
    rubric: RubricCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new grading rubric"""
    try:
        # Create rubric instance
        db_rubric = Rubric(
            name=rubric.name,
            description=rubric.description,
            language=rubric.language,
            criteria=rubric.criteria,
            weights=rubric.weights,
            total_points=rubric.total_points,
            analysis_config=rubric.analysis_config
        )

        db.add(db_rubric)
        await db.commit()
        await db.refresh(db_rubric)

        logger.info("Created rubric", rubric_id=db_rubric.id, name=rubric.name)

        return RubricResponse.model_validate(db_rubric)

    except Exception as e:
        logger.error("Failed to create rubric", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rubric: {str(e)}"
        ) from None


@router.get("/", response_model=list[RubricResponse])
async def list_rubrics(
    language: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all rubrics with optional filtering"""
    try:
        query = select(Rubric)

        if language:
            query = query.where(Rubric.language == language)

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        rubrics = result.scalars().all()

        logger.info("Listed rubrics", count=len(rubrics), language_filter=language)

        return [RubricResponse.model_validate(rubric) for rubric in rubrics]

    except Exception as e:
        logger.error("Failed to list rubrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rubrics: {str(e)}"
        ) from None


@router.get("/{rubric_id}", response_model=RubricResponse)
async def get_rubric(
    rubric_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific rubric by ID"""
    try:
        result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
        rubric = result.scalar_one_or_none()

        if not rubric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rubric {rubric_id} not found"
            ) from None

        logger.info("Retrieved rubric", rubric_id=rubric_id)

        return RubricResponse.model_validate(rubric)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get rubric", rubric_id=rubric_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rubric: {str(e)}"
        ) from None


@router.put("/{rubric_id}", response_model=RubricResponse)
async def update_rubric(
    rubric_id: int,
    rubric_update: RubricCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing rubric"""
    try:
        result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
        rubric = result.scalar_one_or_none()

        if not rubric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rubric {rubric_id} not found"
            ) from None

        # Update rubric fields
        rubric.name = rubric_update.name
        rubric.description = rubric_update.description
        rubric.language = rubric_update.language
        rubric.criteria = rubric_update.criteria
        rubric.weights = rubric_update.weights
        rubric.total_points = rubric_update.total_points
        rubric.analysis_config = rubric_update.analysis_config

        await db.commit()
        await db.refresh(rubric)

        logger.info("Updated rubric", rubric_id=rubric_id)

        return RubricResponse.model_validate(rubric)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update rubric", rubric_id=rubric_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rubric: {str(e)}"
        ) from None


@router.delete("/{rubric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rubric(
    rubric_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a rubric"""
    try:
        result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
        rubric = result.scalar_one_or_none()

        if not rubric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rubric {rubric_id} not found"
            ) from None

        # Check if rubric is being used by assignments
        assignments_result = await db.execute(
            select(Assignment).where(Assignment.rubric_id == rubric_id)
        )
        assignments = assignments_result.scalars().all()

        if assignments:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete rubric: it is used by {len(assignments)} assignment(s)"
            ) from None

        await db.delete(rubric)
        await db.commit()

        logger.info("Deleted rubric", rubric_id=rubric_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete rubric", rubric_id=rubric_id, error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rubric: {str(e)}"
        ) from None


@router.get("/language/{language}", response_model=list[RubricResponse])
async def get_rubrics_by_language(
    language: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all rubrics for a specific programming language"""
    try:
        result = await db.execute(
            select(Rubric).where(Rubric.language == language.lower())
        )
        rubrics = result.scalars().all()

        logger.info("Retrieved rubrics by language", language=language, count=len(rubrics))

        return [RubricResponse.model_validate(rubric) for rubric in rubrics]

    except Exception as e:
        logger.error("Failed to get rubrics by language", language=language, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rubrics for language {language}: {str(e)}"
        ) from None


# Assignment endpoints
@router.post("/assignments/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    assignment: AssignmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new assignment"""
    try:
        # Verify rubric exists
        result = await db.execute(select(Rubric).where(Rubric.id == assignment.rubric_id))
        rubric = result.scalar_one_or_none()

        if not rubric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rubric {assignment.rubric_id} not found"
            ) from None

        # Create assignment instance
        db_assignment = Assignment(
            name=assignment.name,
            description=assignment.description,
            course_id=assignment.course_id,
            course_name=assignment.course_name,
            semester=assignment.semester,
            language=assignment.language,
            rubric_id=assignment.rubric_id,
            requirements=assignment.requirements,
            test_cases=assignment.test_cases,
            starter_code=assignment.starter_code,
            similarity_enabled=assignment.similarity_enabled,
            similarity_threshold=assignment.similarity_threshold,
            cross_cohort_check=assignment.cross_cohort_check,
            due_date=assignment.due_date,
            late_penalty=assignment.late_penalty
        )

        db.add(db_assignment)
        await db.commit()
        await db.refresh(db_assignment)

        logger.info("Created assignment", assignment_id=db_assignment.id, name=assignment.name)

        return AssignmentResponse.model_validate(db_assignment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create assignment", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assignment: {str(e)}"
        ) from None


@router.get("/assignments/", response_model=list[AssignmentResponse])
async def list_assignments(
    course_id: str | None = None,
    language: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List assignments with optional filtering"""
    try:
        query = select(Assignment)

        if course_id:
            query = query.where(Assignment.course_id == course_id)
        if language:
            query = query.where(Assignment.language == language)

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        assignments = result.scalars().all()

        logger.info("Listed assignments", count=len(assignments))

        return [AssignmentResponse.model_validate(assignment) for assignment in assignments]

    except Exception as e:
        logger.error("Failed to list assignments", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list assignments: {str(e)}"
        ) from None


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific assignment by ID"""
    try:
        result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
        assignment = result.scalar_one_or_none()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment {assignment_id} not found"
            ) from None

        logger.info("Retrieved assignment", assignment_id=assignment_id)

        return AssignmentResponse.model_validate(assignment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get assignment", assignment_id=assignment_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assignment: {str(e)}"
        ) from None
