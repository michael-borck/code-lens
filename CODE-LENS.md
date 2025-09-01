# CodeLens - Code Analysis Microservice

**Automated Code Analysis & Grading Assistant for Educators**

## 🎯 Vision

A dedicated microservice for analyzing, validating, and grading student code submissions across multiple programming languages. Designed to help educators provide consistent, comprehensive feedback while reducing manual grading time. Designed for introductor programming courses where a complete development stak, like linters, typecheckers etc may not have been setup.

## 🚀 Core Purpose

Unlike DocumentLens (focused on natural language and academic text), CodeLens specializes in:
- Static code analysis and quality metrics
- Syntax validation and error detection
- Code similarity/plagiarism detection
- Automated test execution
- Grading rubric application
- Constructive feedback generation

## 📊 Target Languages (MVP)

1. **Python** - Full AST analysis, complexity metrics, PEP8 compliance
2. **HTML** - W3C validation, accessibility checks, semantic structure
3. **CSS** - Validation, best practices, browser compatibility
4. **JavaScript** - Syntax validation, ESLint rules, common pitfalls

## 🏗️ Proposed Architecture

```
codelens/
├── app/
│   ├── analyzers/
│   │   ├── python_analyzer.py      # AST parsing, complexity, style
│   │   ├── html_analyzer.py        # Structure, validation, accessibility
│   │   ├── css_analyzer.py         # Validation, best practices
│   │   ├── js_analyzer.py          # Syntax, linting, patterns
│   │   └── similarity_checker.py   # Cross-submission similarity
│   │
│   ├── services/
│   │   ├── code_executor.py        # Safe code execution sandbox
│   │   ├── test_runner.py          # Run unit tests
│   │   ├── w3c_validator.py        # W3C API integration
│   │   ├── feedback_generator.py   # AI-assisted feedback
│   │   └── rubric_evaluator.py     # Apply grading rubrics
│   │
│   ├── validators/
│   │   ├── syntax_validator.py     # Language-specific syntax checks
│   │   ├── security_scanner.py     # Security vulnerability detection
│   │   └── best_practices.py       # Coding standards enforcement
│   │
│   └── api/
│       └── routes/
│           ├── analyze.py          # Single file analysis
│           ├── batch.py            # Batch submission processing
│           ├── rubric.py           # Rubric management
│           └── reports.py          # Grade report generation
```

## 🔧 Key Features

### 1. Code Quality Analysis
- **Complexity Metrics**: Cyclomatic complexity, nesting depth, LOC
- **Style Compliance**: PEP8 (Python), ESLint (JS), W3C (HTML/CSS)
- **Code Smells**: Duplicate code, long methods, unused variables
- **Documentation**: Docstring coverage, comment quality

### 2. Correctness Validation
- **Syntax Checking**: Language-specific parsers
- **Type Checking**: Static type analysis where applicable
- **Logic Errors**: Common mistakes and anti-patterns
- **Output Validation**: Expected vs actual output comparison

### 3. Plagiarism Detection
- **Structural Similarity**: AST-based comparison
- **Token Analysis**: Variable renaming detection
- **Cross-Cohort**: Compare across student submissions
- **External Sources**: Check against online repositories

### 4. Educational Feedback
- **Constructive Comments**: Explain what's wrong and why
- **Improvement Suggestions**: How to fix issues
- **Learning Resources**: Links to relevant documentation
- **Progress Tracking**: Performance over time

## 📡 API Design

### Core Endpoints

```
POST /api/analyze/python
POST /api/analyze/web       # HTML/CSS/JS bundle
POST /api/analyze/batch      # Multiple submissions

GET  /api/rubrics           # Available grading rubrics
POST /api/rubrics           # Create custom rubric

POST /api/compare           # Similarity checking
GET  /api/reports/{id}      # Detailed analysis report
```

### Example Request/Response

```json
// Request
{
  "code": "def calculate_grade(score):\n    return score * 100",
  "language": "python",
  "rubric_id": "intro-python-assignment-1",
  "check_similarity": true,
  "cohort_id": "CS101-2024"
}

// Response
{
  "analysis": {
    "syntax": {
      "valid": true,
      "errors": []
    },
    "quality": {
      "complexity": 1,
      "style_issues": [
        {
          "line": 1,
          "issue": "Missing function docstring",
          "severity": "minor"
        }
      ]
    },
    "correctness": {
      "test_results": "3/5 passed",
      "logic_issues": ["No input validation"]
    },
    "similarity": {
      "highest_match": 0.15,
      "flagged": false
    }
  },
  "grade": {
    "score": 75,
    "breakdown": {
      "functionality": 30,
      "style": 15,
      "documentation": 10,
      "testing": 20
    }
  },
  "feedback": {
    "strengths": ["Clean function structure"],
    "improvements": ["Add input validation", "Include docstring"],
    "resources": ["https://peps.python.org/pep-0257/"]
  }
}
```

## 🛠️ Technology Stack

### Core Dependencies
- **Python Analysis** (configurable options): `ast`, `pylint`, `mypy`, `black`, `radon`, `ruff`, `basedpyright`
- **Web Validation**: `html5lib`, `cssutils`, `beautifulsoup4`
- **JavaScript**: `esprima` (via subprocess), `jshint`
- **Similarity**: `difflib`, `python-Levenshtein`, custom AST comparison
- **Sandboxing**: `docker` or `firejail` for safe execution

### External Services
- **W3C Validator**: Optional for official HTML/CSS validation
- **GitHub API**: Check against public repositories
- **OpenAI API**: Optional for enhanced feedback generation

## 🚦 Implementation Phases

### Phase 1: Python Analysis (Week 1-2)
- AST-based analysis
- Style checking (PEP8)
- Basic complexity metrics
- Simple test runner

### Phase 2: Web Technologies (Week 3-4)
- HTML structure validation
- CSS validation
- JavaScript syntax checking
- Basic accessibility checks

### Phase 3: Similarity Detection (Week 5)
- Token-based comparison
- AST structural similarity
- Cohort-wide checking

### Phase 4: Grading & Feedback (Week 6)
- Rubric system
- Automated scoring
- Feedback generation
- Report creation

## 🔒 Security Considerations

1. **Code Execution Sandbox**: Never execute student code directly
2. **Resource Limits**: CPU, memory, and time constraints
3. **Input Sanitization**: Prevent injection attacks
4. **Access Control**: Educator-only endpoints
5. **Data Privacy**: Secure storage of student submissions

## 📈 Future Enhancements

- **More Languages**: Java, C++, SQL, R
- **IDE Integration**: VS Code extension
- **Real-time Analysis**: Live coding feedback
- **Peer Review**: Student cross-evaluation
- **Learning Analytics**: Track common mistakes
- **AI Tutoring**: Personalized learning paths

## 🎓 Educational Impact

CodeLens aims to:
- Provide consistent, objective grading
- Reduce educator workload
- Give students immediate feedback
- Identify struggling students early
- Track learning progress over time
- Encourage best practices from the start

---

*CodeLens: Empowering educators with intelligent code analysis*
