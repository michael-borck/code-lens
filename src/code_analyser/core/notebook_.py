# src/code_analyser/core/notebook_.py
from __future__ import annotations
import json

from ..models import NotebookMetrics
from .python_ import analyse_python

_MAGIC_PREFIXES = ("%", "%%")


def analyse_notebook(content: bytes) -> NotebookMetrics:
    try:
        nb = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return NotebookMetrics(
            code_cell_count=0, markdown_cell_count=0, has_outputs=False,
            output_cell_count=0, execution_order_valid=True, magic_command_count=0,
            python_metrics=None,
        )

    cells = nb.get("cells", [])
    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    md_cells = [c for c in cells if c.get("cell_type") == "markdown"]

    output_cell_count = sum(1 for c in code_cells if c.get("outputs"))
    has_outputs = output_cell_count > 0

    exec_counts = [c.get("execution_count") for c in code_cells if c.get("execution_count") is not None]
    if exec_counts:
        execution_order_valid = exec_counts == list(range(exec_counts[0], exec_counts[0] + len(exec_counts)))
    else:
        execution_order_valid = True

    magic_count = 0
    code_lines: list[str] = []
    for cell in code_cells:
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        for line in source.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(p) for p in _MAGIC_PREFIXES):
                magic_count += 1
            else:
                code_lines.append(line)

    combined_code = "\n".join(code_lines)
    try:
        python_metrics = analyse_python(combined_code) if combined_code.strip() else None
    except Exception:
        python_metrics = None

    return NotebookMetrics(
        code_cell_count=len(code_cells),
        markdown_cell_count=len(md_cells),
        has_outputs=has_outputs,
        output_cell_count=output_cell_count,
        execution_order_valid=execution_order_valid,
        magic_command_count=magic_count,
        python_metrics=python_metrics,
    )
