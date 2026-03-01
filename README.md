# CodeLens

<!-- BADGES:START -->
[![edtech](https://img.shields.io/badge/-edtech-4caf50?style=flat-square)](https://github.com/topics/edtech) [![automated-grading](https://img.shields.io/badge/-automated--grading-blue?style=flat-square)](https://github.com/topics/automated-grading) [![code-analysis](https://img.shields.io/badge/-code--analysis-blue?style=flat-square)](https://github.com/topics/code-analysis) [![docker](https://img.shields.io/badge/-docker-2496ed?style=flat-square)](https://github.com/topics/docker) [![education](https://img.shields.io/badge/-education-blue?style=flat-square)](https://github.com/topics/education) [![fastapi](https://img.shields.io/badge/-fastapi-009688?style=flat-square)](https://github.com/topics/fastapi) [![microservice](https://img.shields.io/badge/-microservice-blue?style=flat-square)](https://github.com/topics/microservice) [![plagiarism-detection](https://img.shields.io/badge/-plagiarism--detection-blue?style=flat-square)](https://github.com/topics/plagiarism-detection) [![python](https://img.shields.io/badge/-python-3776ab?style=flat-square)](https://github.com/topics/python) [![static-analysis](https://img.shields.io/badge/-static--analysis-blue?style=flat-square)](https://github.com/topics/static-analysis)
<!-- BADGES:END -->

**Automated Code Analysis & Grading Assistant for Educators**

CodeLens is a comprehensive microservice designed to help educators analyze, validate, and grade student code submissions across multiple programming languages. It provides automated analysis, plagiarism detection, sandboxed code execution, and detailed feedback generation.

## 🚀 Features

### Core Analysis
- **Static Code Analysis**: Syntax validation, style checking, complexity metrics
- **Configurable Tools**: Support for ruff, mypy, and other analysis tools
- **Multi-language Support**: Currently supports Python with extensible architecture
- **Quality Metrics**: Lines of code, cyclomatic complexity, maintainability index

### Code Execution
- **Secure Sandboxing**: Docker-based isolated execution environment
- **Test Execution**: Support for pytest and unittest frameworks
- **Resource Limits**: CPU, memory, and time constraints for safety
- **Input/Output Validation**: Compare expected vs actual outputs

### Plagiarism Detection
- **Multiple Methods**: AST structural, token-based, line-based similarity
- **Cross-submission Comparison**: Compare against other student submissions
- **Configurable Thresholds**: Adjustable similarity detection sensitivity
- **Review System**: Manual review and flagging of potential plagiarism

### Batch Processing
- **Directory Processing**: Analyze entire folders of submissions
- **Parallel Processing**: Concurrent analysis for improved performance
- **Student Info Extraction**: Automatic extraction of student IDs from filenames
- **CLI Interface**: Command-line tools for instructors

### Grading & Feedback
- **Rubric-based Grading**: Configurable grading criteria and weights
- **Automated Scoring**: Calculate grades based on multiple factors
- **Detailed Feedback**: Constructive comments and improvement suggestions
- **Progress Tracking**: Track student performance over time

## 🏗️ Architecture

```
codelens/
├── api/                 # FastAPI routes and schemas
├── analyzers/           # Code analysis engines
├── services/            # Business logic services
├── models/              # Database models
├── db/                  # Database configuration
├── core/                # Configuration and settings
└── utils/               # Utility functions
```

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd code-lens
```

2. **Install dependencies**
```bash
pip install -e .
```

3. **Install analysis tools**
```bash
pip install ruff mypy pytest
```

4. **Setup Docker** (for code execution)
```bash
docker pull python:3.11-slim
```

5. **Initialize database**
```bash
python -m codelens.main
```

## 🚀 Quick Start

### Web API Server

Start the FastAPI server:

```bash
# Development mode
uvicorn codelens.main:app --reload

# Production mode
uvicorn codelens.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8003` with documentation at `/docs`.

### CLI Usage

Analyze a single file:
```bash
python -m codelens analyze submission.py --student-id cs123456
```

Process a directory of submissions:
```bash
python -m codelens batch /path/to/submissions --language python --detailed
```

Generate batch report:
```bash
python -m codelens batch /submissions --output results.json --rubric-id 1
```

## 📡 API Examples

### Analyze Python Code
```bash
curl -X POST "http://localhost:8003/api/v1/analyze/python" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello():\n    print(\"Hello, World!\")",
    "language": "python",
    "student_id": "cs123456",
    "check_similarity": true,
    "run_tests": false
  }'
```

### Batch Analysis
```bash
curl -X POST "http://localhost:8003/api/v1/analyze/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {"code": "def add(a, b): return a + b", "path": "student1.py"},
      {"code": "def multiply(x, y): return x * y", "path": "student2.py"}
    ],
    "language": "python",
    "check_similarity": true
  }'
```

### Create Rubric
```bash
curl -X POST "http://localhost:8003/api/v1/rubrics/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Assignment 1",
    "language": "python",
    "criteria": {"functionality": 40, "style": 30, "documentation": 30},
    "weights": {"functionality": 0.4, "style": 0.3, "documentation": 0.3},
    "total_points": 100
  }'
```

## ⚙️ Configuration

Configuration is managed through environment variables and the `codelens/core/config.py` file:

```python
# Analysis tools
RUFF_ENABLED=true
MYPY_ENABLED=true
MAX_LINE_LENGTH=88

# Execution limits
EXECUTION_TIMEOUT=30
MEMORY_LIMIT=128m
CPU_LIMIT=0.5

# Similarity detection
SIMILARITY_ENABLED=true
SIMILARITY_THRESHOLD=0.8

# Database
DATABASE_URL=sqlite+aiosqlite:///./codelens.db
```

## 🔒 Security

- **Sandboxed Execution**: All code runs in isolated Docker containers
- **Resource Limits**: CPU, memory, and time constraints prevent abuse
- **No Network Access**: Containers run without network connectivity
- **Input Validation**: All inputs are validated and sanitized
- **Code Analysis Only**: Original submissions are not stored permanently

## 📊 Supported Analysis

### Python
- **Linting**: ruff (configurable rules)
- **Type Checking**: mypy (optional)
- **Metrics**: Complexity, maintainability, documentation coverage
- **Testing**: pytest, unittest support
- **Similarity**: AST-based structural comparison

### Future Languages
The architecture supports extension to JavaScript, HTML/CSS, Java, and other languages.

## 🤝 Educational Use Cases

- **Introductory Programming Courses**: Automated grading for basic assignments
- **Code Quality Assessment**: Teaching best practices and style guidelines
- **Plagiarism Detection**: Identifying potential academic dishonesty
- **Progress Tracking**: Monitoring student improvement over time
- **Immediate Feedback**: Helping students learn from mistakes

## 📈 Example Workflow

1. **Instructor**: Creates assignment with rubric
2. **Students**: Submit code files (via LMS or direct upload)
3. **CodeLens**: Analyzes submissions automatically
4. **System**: Generates grades and detailed feedback
5. **Instructor**: Reviews flagged similarities and edge cases
6. **Students**: Receive feedback and suggestions for improvement

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=codelens tests/
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with FastAPI for high-performance web APIs
- Uses Docker for secure code execution
- Powered by ruff and mypy for Python analysis
- Inspired by the need for fair and consistent code grading

---

**CodeLens**: Empowering educators with intelligent code analysis 🔍✨