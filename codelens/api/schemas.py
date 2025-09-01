"""
Pydantic schemas for API request/response models
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator

from codelens.analyzers.base import Severity


class AnalysisLanguage(str, Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    HTML = "html"
    CSS = "css"


class AnalysisIssueSchema(BaseModel):
    """Schema for analysis issues"""
    line: int = Field(..., ge=1, description="Line number where issue occurs")
    column: int = Field(0, ge=0, description="Column position")
    severity: Severity = Field(..., description="Issue severity level")
    code: str = Field("", description="Error/warning code")
    message: str = Field(..., description="Issue description")
    category: str = Field("general", description="Issue category")
    suggestion: str | None = Field(None, description="How to fix the issue")


class CodeMetricsSchema(BaseModel):
    """Schema for code quality metrics"""
    lines_of_code: int = Field(0, ge=0)
    lines_of_comments: int = Field(0, ge=0)
    blank_lines: int = Field(0, ge=0)
    cyclomatic_complexity: int = Field(0, ge=0)
    cognitive_complexity: int = Field(0, ge=0)
    function_count: int = Field(0, ge=0)
    class_count: int = Field(0, ge=0)
    max_nesting_depth: int = Field(0, ge=0)
    maintainability_index: float = Field(0.0, ge=0.0, le=100.0)


class TestCaseSchema(BaseModel):
    """Schema for test case definition"""
    name: str = Field(..., description="Test case name")
    function: str = Field("main", description="Function to test")
    inputs: list[Any] = Field(default_factory=list, description="Function inputs")
    expected: Any = Field(None, description="Expected output")
    description: str | None = Field(None, description="Test description")


class AnalysisRequest(BaseModel):
    """Request schema for code analysis"""
    code: str = Field(..., min_length=1, description="Source code to analyze")
    language: AnalysisLanguage = Field(AnalysisLanguage.PYTHON, description="Programming language")
    rubric_id: int | None = Field(None, description="Rubric ID for grading")
    assignment_id: int | None = Field(None, description="Assignment ID")

    # Student information (optional)
    student_id: str | None = Field(None, description="Student identifier")
    student_name: str | None = Field(None, description="Student name")

    # Analysis options
    check_similarity: bool = Field(True, description="Enable similarity checking")
    run_tests: bool = Field(False, description="Run test cases")
    test_cases: list[TestCaseSchema] | None = Field(None, description="Custom test cases")

    # Execution options
    execute_code: bool = Field(False, description="Execute code in sandbox")
    input_data: str | None = Field(None, description="Input data for execution")

    # Analysis configuration overrides
    analyzer_config: dict[str, Any] | None = Field(None, description="Custom analyzer config")

    @validator('code')
    def validate_code_length(cls, v):
        if len(v.encode('utf-8')) > 1024 * 1024:  # 1MB limit
            raise ValueError('Code size exceeds 1MB limit')
        return v


class BatchAnalysisRequest(BaseModel):
    """Request schema for batch analysis"""
    files: list[dict[str, str]] = Field(..., min_items=1, description="List of files with code and path")
    language: AnalysisLanguage = Field(AnalysisLanguage.PYTHON, description="Programming language")
    assignment_id: int | None = Field(None, description="Assignment ID")
    rubric_id: int | None = Field(None, description="Rubric ID for grading")

    # Batch options
    check_similarity: bool = Field(True, description="Enable cross-submission similarity checking")
    parallel_processing: bool = Field(True, description="Process files in parallel")

    @validator('files')
    def validate_files(cls, v):
        if len(v) > 100:  # Max 100 files per batch
            raise ValueError('Maximum 100 files per batch')
        for file_info in v:
            if 'code' not in file_info or 'path' not in file_info:
                raise ValueError('Each file must have code and path fields')
        return v


class ExecutionResultSchema(BaseModel):
    """Schema for code execution results"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    memory_used: str | None = None
    timed_out: bool = False
    error_message: str | None = None


class TestResultSchema(BaseModel):
    """Schema for test execution results"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: list[dict[str, Any]] = Field(default_factory=list)
    test_output: str = ""
    execution_result: ExecutionResultSchema | None = None


class SimilarityResultSchema(BaseModel):
    """Schema for similarity analysis results"""
    highest_similarity: float = Field(0.0, ge=0.0, le=1.0)
    flagged_submissions: list[dict[str, Any]] = Field(default_factory=list)
    ai_baseline_similarity: float | None = Field(None, ge=0.0, le=1.0)
    methods_used: list[str] = Field(default_factory=list)


class GradeBreakdownSchema(BaseModel):
    """Schema for grade breakdown by category"""
    functionality: float = Field(0.0, ge=0.0, le=100.0)
    style: float = Field(0.0, ge=0.0, le=100.0)
    documentation: float = Field(0.0, ge=0.0, le=100.0)
    testing: float = Field(0.0, ge=0.0, le=100.0)
    total: float = Field(0.0, ge=0.0, le=100.0)


class FeedbackSchema(BaseModel):
    """Schema for feedback and recommendations"""
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    detailed_comments: dict[str, str] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    """Response schema for code analysis"""
    success: bool
    submission_id: str = Field(..., description="Unique submission identifier")

    # Analysis results
    syntax_valid: bool = True
    syntax_errors: list[AnalysisIssueSchema] = Field(default_factory=list)
    issues: list[AnalysisIssueSchema] = Field(default_factory=list)
    metrics: CodeMetricsSchema = Field(default_factory=CodeMetricsSchema)

    # Execution results (if requested)
    execution_result: ExecutionResultSchema | None = None
    test_result: TestResultSchema | None = None

    # Similarity results (if enabled)
    similarity_result: SimilarityResultSchema | None = None

    # Grading results (if rubric provided)
    grade_breakdown: GradeBreakdownSchema | None = None
    total_score: float | None = Field(None, ge=0.0, le=100.0)
    max_score: float = Field(100.0, ge=0.0)

    # Feedback
    feedback: FeedbackSchema = Field(default_factory=FeedbackSchema)

    # Metadata
    analysis_version: str = ""
    processing_time: float = 0.0
    tools_used: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Error information
    error_message: str | None = None


class BatchAnalysisResponse(BaseModel):
    """Response schema for batch analysis"""
    success: bool
    batch_id: str = Field(..., description="Unique batch identifier")
    total_files: int = Field(..., ge=0)
    processed_files: int = Field(..., ge=0)
    failed_files: int = Field(..., ge=0)

    # Individual results
    results: list[AnalysisResponse] = Field(default_factory=list)

    # Batch-level similarity analysis
    cross_similarity_results: list[dict[str, Any]] | None = None

    # Timing information
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0

    # Status
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = None


# Rubric schemas
class RubricCriterionCreate(BaseModel):
    """Schema for creating a rubric criterion"""
    name: str = Field(..., max_length=100)
    description: str
    category: str = Field(..., max_length=50)
    max_points: int = Field(..., gt=0)
    weight: float = Field(1.0, gt=0.0)
    auto_gradable: bool = True
    evaluation_method: str | None = Field(None, max_length=50)
    evaluation_config: dict[str, Any] | None = None
    performance_levels: dict[str, Any] = Field(..., description="Performance level definitions")


class RubricCreate(BaseModel):
    """Schema for creating a rubric"""
    name: str = Field(..., max_length=200)
    description: str | None = None
    language: str = Field(..., max_length=50)
    criteria: dict[str, Any] = Field(..., description="Grading criteria")
    weights: dict[str, float] = Field(..., description="Category weights")
    total_points: int = Field(100, gt=0)
    analysis_config: dict[str, Any] | None = None


class RubricResponse(BaseModel):
    """Schema for rubric response"""
    id: int
    name: str
    description: str | None = None
    language: str
    criteria: dict[str, Any]
    weights: dict[str, float]
    total_points: int
    analysis_config: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Assignment schemas
class AssignmentCreate(BaseModel):
    """Schema for creating an assignment"""
    name: str = Field(..., max_length=200)
    description: str
    course_id: str | None = Field(None, max_length=50)
    course_name: str | None = Field(None, max_length=200)
    semester: str | None = Field(None, max_length=20)
    language: str = Field(..., max_length=50)
    rubric_id: int
    requirements: dict[str, Any] = Field(..., description="Technical requirements")
    test_cases: dict[str, Any] | None = None
    starter_code: str | None = None
    similarity_enabled: bool = True
    similarity_threshold: float = Field(0.8, ge=0.0, le=1.0)
    cross_cohort_check: bool = False
    due_date: datetime | None = None
    late_penalty: float | None = Field(None, ge=0.0)


class AssignmentResponse(BaseModel):
    """Schema for assignment response"""
    id: int
    name: str
    description: str
    course_id: str | None = None
    course_name: str | None = None
    semester: str | None = None
    language: str
    rubric_id: int
    requirements: dict[str, Any]
    test_cases: dict[str, Any] | None = None
    starter_code: str | None = None
    similarity_enabled: bool
    similarity_threshold: float
    cross_cohort_check: bool
    due_date: datetime | None = None
    late_penalty: float | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
