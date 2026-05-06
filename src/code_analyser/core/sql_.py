# src/code_analyser/core/sql_.py
from __future__ import annotations
import re

import sqlparse
from sqlparse.sql import Where

from ..models import SQLMetrics

_JOIN_RE = re.compile(r"\bJOIN\b", re.IGNORECASE)
_SELECT_STAR_RE = re.compile(r"\bSELECT\s+\*", re.IGNORECASE)


def analyse_sql(source: str) -> SQLMetrics:
    statements = [s for s in sqlparse.parse(source) if str(s).strip()]

    query_types: dict[str, int] = {}
    join_count = 0
    unsafe: list[str] = []

    for stmt in statements:
        stype = (stmt.get_type() or "UNKNOWN").upper()
        query_types[stype] = query_types.get(stype, 0) + 1

        stmt_str = str(stmt)
        join_count += len(_JOIN_RE.findall(stmt_str))

        if stype == "UPDATE" and not any(isinstance(tok, Where) for tok in stmt.tokens):
            unsafe.append("UPDATE without WHERE")
        elif stype == "DELETE" and not any(isinstance(tok, Where) for tok in stmt.tokens):
            unsafe.append("DELETE without WHERE")
        if _SELECT_STAR_RE.search(stmt_str):
            unsafe.append("SELECT *")

    subquery_depth = _max_subquery_depth(source)

    return SQLMetrics(
        statement_count=len(statements),
        query_types=query_types,
        join_count=join_count,
        subquery_depth=subquery_depth,
        unsafe_patterns=list(dict.fromkeys(unsafe)),
    )


def _max_subquery_depth(source: str) -> int:
    depth = 0
    max_depth = 0
    for ch in source:
        if ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")":
            depth = max(0, depth - 1)
    return max_depth
