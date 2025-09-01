"""Utility functions"""

from .helpers import (
    calculate_file_hash,
    calculate_grade_letter,
    detect_language_from_extension,
    extract_classes_from_python,
    extract_functions_from_python,
    format_file_size,
    generate_submission_id,
    is_supported_file_type,
    parse_batch_files,
    sanitize_code_for_display,
    validate_student_id,
)

__all__ = [
    "generate_submission_id",
    "calculate_file_hash",
    "detect_language_from_extension",
    "is_supported_file_type",
    "format_file_size",
    "extract_functions_from_python",
    "extract_classes_from_python",
    "sanitize_code_for_display",
    "calculate_grade_letter",
    "validate_student_id",
    "parse_batch_files"
]
