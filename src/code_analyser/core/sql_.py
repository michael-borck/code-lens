# src/code_analyser/core/sql_.py
from __future__ import annotations
import re

import sqlparse
from sqlparse.sql import Parenthesis, Where
from sqlparse.tokens import DML, Punctuation

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


def _paren_starts_with_select(token: Parenthesis) -> bool:
    """True iff the first non-whitespace token after ``(`` is a SELECT DML."""
    for t in token.flatten():
        if t.is_whitespace:
            continue
        if t.ttype is Punctuation and t.value == "(":
            continue
        return t.ttype is DML and t.value.upper() == "SELECT"
    return False


def _walk(token, current_depth: int, current_max: int) -> int:
    if isinstance(token, Parenthesis) and _paren_starts_with_select(token):
        current_depth += 1
        current_max = max(current_max, current_depth)
    if hasattr(token, "tokens"):
        for child in token.tokens:
            current_max = _walk(child, current_depth, current_max)
    return current_max


def _max_subquery_depth(source: str) -> int:
    """Return the maximum nesting depth of SELECT statements.

    A top-level SELECT is depth 1. A subquery (a ``Parenthesis`` whose
    first non-whitespace token is a SELECT keyword) inside another
    SELECT is depth 2. Subquery-in-subquery is depth 3. Etc.

    Walks the sqlparse token tree so that non-subquery parens — e.g.
    ``VALUES (...)``, ``CAST(x AS y)``, or arithmetic ``(a + (b + c))`` —
    do NOT inflate the count.
    """
    parsed = sqlparse.parse(source)
    max_depth = 0
    for stmt in parsed:
        # Top-level SELECT counts as depth 1.
        for t in stmt.flatten():
            if t.is_whitespace:
                continue
            if t.ttype is DML and t.value.upper() == "SELECT":
                max_depth = max(max_depth, 1)
            break
        for tok in stmt.tokens:
            max_depth = max(max_depth, _walk(tok, 1, max_depth))
    return max_depth
