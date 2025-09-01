"""
Utility functions and helpers
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any


def generate_submission_id() -> str:
    """Generate a unique submission identifier"""
    return str(uuid.uuid4())


def calculate_file_hash(content: str) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def detect_language_from_extension(filename: str) -> str | None:
    """Detect programming language from file extension"""
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript'
    }

    ext = Path(filename).suffix.lower()
    return extension_map.get(ext)


def is_supported_file_type(filename: str) -> bool:
    """Check if file type is supported for analysis"""
    return detect_language_from_extension(filename) is not None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def extract_functions_from_python(code: str) -> list[dict[str, Any]]:
    """Extract function information from Python code"""
    import ast

    functions = []
    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'has_docstring': (
                        len(node.body) > 0 and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)
                    )
                })
    except SyntaxError:
        pass

    return functions


def extract_classes_from_python(code: str) -> list[dict[str, Any]]:
    """Extract class information from Python code"""
    import ast

    classes = []
    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        methods.append({
                            'name': child.name,
                            'line': child.lineno
                        })

                classes.append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': methods,
                    'base_classes': [base.id for base in node.bases if isinstance(base, ast.Name)]
                })
    except SyntaxError:
        pass

    return classes


def sanitize_code_for_display(code: str, max_lines: int = 100) -> str:
    """Sanitize code for safe display, truncating if too long"""
    lines = code.split('\n')

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"... (truncated, {len(code.split(chr(10))) - max_lines} more lines)")

    return '\n'.join(lines)


def calculate_grade_letter(score: float) -> str:
    """Convert numeric score to letter grade"""
    if score >= 97:
        return "A+"
    elif score >= 93:
        return "A"
    elif score >= 90:
        return "A-"
    elif score >= 87:
        return "B+"
    elif score >= 83:
        return "B"
    elif score >= 80:
        return "B-"
    elif score >= 77:
        return "C+"
    elif score >= 73:
        return "C"
    elif score >= 70:
        return "C-"
    elif score >= 67:
        return "D+"
    elif score >= 63:
        return "D"
    elif score >= 60:
        return "D-"
    else:
        return "F"


def validate_student_id(student_id: str) -> bool:
    """Validate student ID format (basic validation)"""
    if not student_id:
        return False

    # Remove whitespace
    student_id = student_id.strip()

    # Check length (between 3 and 50 characters)
    if len(student_id) < 3 or len(student_id) > 50:
        return False

    # Allow alphanumeric characters, hyphens, and underscores
    import re
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', student_id))


def parse_batch_files(files_data: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Parse and validate batch file data"""
    parsed_files = []

    for i, file_data in enumerate(files_data):
        try:
            # Validate required fields
            if 'code' not in file_data or 'path' not in file_data:
                continue

            code = file_data['code']
            file_path = file_data['path']

            # Detect language
            language = detect_language_from_extension(file_path)
            if not language:
                continue

            # Extract metadata
            parsed_file = {
                'index': i,
                'code': code,
                'path': file_path,
                'language': language,
                'size': len(code.encode('utf-8')),
                'hash': calculate_file_hash(code),
                'student_id': file_data.get('student_id'),
                'student_name': file_data.get('student_name')
            }

            parsed_files.append(parsed_file)

        except Exception:
            # Log error but continue processing other files
            continue

    return parsed_files
