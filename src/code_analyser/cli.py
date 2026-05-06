from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

from .pipeline import CodeAnalyser


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        _serve(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(
        prog="code-analyser",
        description="Source code signals analyser",
    )
    parser.add_argument("file", type=Path, help="Source file or .zip archive to analyse")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    parser.add_argument("--llm", action="store_true", help="Include LLM quality signals (requires [llm] extra)")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        result = CodeAnalyser().analyse(args.file, llm=args.llm)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        print(result.model_dump_json(indent=2))
        return

    _print_human(result)


def _print_human(result: CodeAnalysis) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console(file=sys.stdout)
    console.print(
        f"[bold]Input:[/bold] {result.input}  "
        f"[bold]Files:[/bold] {result.file_count}  "
        f"[bold]Languages:[/bold] {', '.join(result.languages_detected)}"
    )

    table = Table(show_header=True, header_style="bold")
    table.add_column("File")
    table.add_column("Language")
    table.add_column("Details")

    for f in result.files:
        details = _summarise_metrics(f.metrics, f.language)
        table.add_row(f.filename, f.language, details)

    console.print(table)

    if result.cross_file.unrecognised_files:
        console.print(f"[dim]Unrecognised: {', '.join(result.cross_file.unrecognised_files)}[/dim]")


def _summarise_metrics(metrics, language: str) -> str:
    if metrics is None:
        return "parse failed"
    if language == "python":
        return (
            f"loc={metrics.loc}  funcs={metrics.function_count}  "
            f"errors={metrics.lint_error_count}  complexity={metrics.cyclomatic_complexity:.1f}"
        )
    if language == "notebook":
        return (
            f"code_cells={metrics.code_cell_count}  "
            f"outputs={'yes' if metrics.has_outputs else 'no'}  "
            f"order={'ok' if metrics.execution_order_valid else 'scrambled'}"
        )
    if language == "html":
        return (
            f"errors={metrics.parse_error_count}  divs={metrics.div_count}  "
            f"semantics={metrics.semantic_element_count}  "
            f"alt={metrics.img_alt_coverage:.0%}"
        )
    if language == "css":
        return f"rules={metrics.rule_count}  layout={metrics.dominant_layout}"
    if language in ("javascript", "typescript"):
        return (
            f"funcs={metrics.function_count}  arrows={metrics.arrow_function_count}  "
            f"console_logs={metrics.console_log_count}"
        )
    if language == "sql":
        return f"statements={metrics.statement_count}  joins={metrics.join_count}"
    return ""


def _serve(argv: list[str]) -> None:
    import uvicorn
    parser = argparse.ArgumentParser(prog="code-analyser serve")
    parser.add_argument("--port", type=int, default=int(os.getenv("CODE_ANALYSER_PORT", "8004")))
    parser.add_argument("--host", default=os.getenv("CODE_ANALYSER_HOST", "127.0.0.1"))
    args = parser.parse_args(argv)
    uvicorn.run("code_analyser.api:app", host=args.host, port=args.port)
