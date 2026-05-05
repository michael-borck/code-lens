"""Family-consistent CLI entry point for code-analyser.

Usage:
  code-analyser submission.py
  code-analyser submission.py --json
  code-analyser serve
  code-analyser serve --port 8004 --host 0.0.0.0
"""

import asyncio
import json
import os
import sys
from pathlib import Path


def main() -> None:
    import argparse

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        _main_serve(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(
        prog="code-analyser",
        description="Source code style, complexity, and quality analysis",
    )
    parser.add_argument("file", type=Path, help="Source file to analyse")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output raw JSON")
    asyncio.run(_cmd_analyse(parser.parse_args()))


def _main_serve(argv: list[str]) -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="code-analyser serve", description="Start the HTTP server")
    parser.add_argument("--port", type=int, default=int(os.getenv("CODE_LENS_PORT", "8004")))
    parser.add_argument("--host", default=os.getenv("CODE_LENS_HOST", "127.0.0.1"))
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development only)")
    _cmd_serve(parser.parse_args(argv))


async def _cmd_analyse(args) -> None:
    from .analyzers.python_analyzer import PythonAnalyzer

    path: Path = args.file
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()
    if suffix != ".py":
        print(f"Error: unsupported file type '{suffix}' — currently supports .py only", file=sys.stderr)
        sys.exit(1)

    code = path.read_text(encoding="utf-8", errors="replace")
    result = await PythonAnalyzer().analyze(code, file_path=str(path))

    output = {
        "language": "python",
        "file_path": str(path.resolve()),
        "file_size": path.stat().st_size,
        "metrics": {
            "lines_of_code": result.metrics.lines_of_code,
            "blank_lines": result.metrics.blank_lines,
            "comment_lines": result.metrics.lines_of_comments,
            "function_count": result.metrics.function_count,
            "class_count": result.metrics.class_count,
            "cyclomatic_complexity": result.metrics.cyclomatic_complexity,
            "max_nesting_depth": result.metrics.max_nesting_depth,
        },
        "issues": [
            {
                "rule": i.rule_id,
                "line": i.line,
                "column": i.column,
                "severity": i.severity.value,
                "message": i.message,
            }
            for i in result.issues
        ],
        "summary": {
            "error_count": sum(1 for i in result.issues if i.severity.value == "error"),
            "warning_count": sum(1 for i in result.issues if i.severity.value == "warning"),
            "style_count": sum(1 for i in result.issues if i.severity.value == "style"),
            "total_issues": len(result.issues),
        },
    }

    if args.as_json:
        print(json.dumps(output, indent=2))
        return

    m = output["metrics"]
    s = output["summary"]
    print(f"File:        {path.name}")
    print(f"Lines:       {m['lines_of_code']} code, {m['blank_lines']} blank, {m['comment_lines']} comments")
    print(f"Functions:   {m['function_count']}  Classes: {m['class_count']}")
    if m["cyclomatic_complexity"]:
        print(f"Complexity:  {m['cyclomatic_complexity']} (max nesting: {m['max_nesting_depth']})")
    print(f"Issues:      {s['total_issues']} ({s['error_count']} errors, {s['warning_count']} warnings, {s['style_count']} style)")

    if output["issues"]:
        print()
        for issue in output["issues"][:20]:
            col = f":{issue['column']}" if issue["column"] else ""
            print(f"  line {issue['line']}{col}  [{issue['rule']}]  {issue['message']}")
        if len(output["issues"]) > 20:
            print(f"  ... and {len(output['issues']) - 20} more")


def _cmd_serve(args) -> None:
    import uvicorn
    uvicorn.run(
        "code_analyser.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
