from conftest import VALID_SQL, UNSAFE_SQL
from code_analyser.core.sql_ import analyse_sql


def test_statement_count():
    m = analyse_sql(VALID_SQL)
    assert m.statement_count == 5


def test_query_types():
    m = analyse_sql(VALID_SQL)
    assert m.query_types.get("SELECT", 0) >= 1
    assert m.query_types.get("INSERT", 0) == 1
    assert m.query_types.get("UPDATE", 0) == 1
    assert m.query_types.get("DELETE", 0) == 1


def test_join_count():
    m = analyse_sql(VALID_SQL)
    assert m.join_count == 1


def test_no_unsafe_patterns():
    m = analyse_sql(VALID_SQL)
    assert m.unsafe_patterns == []


def test_unsafe_patterns():
    """UNSAFE_SQL fixture: UPDATE-without-WHERE, DELETE-without-WHERE, SELECT *
    — assert each pattern fired explicitly rather than hiding behind an or-chain.
    """
    m = analyse_sql(UNSAFE_SQL)
    assert len(m.unsafe_patterns) == 3
    assert "UPDATE without WHERE" in m.unsafe_patterns
    assert "DELETE without WHERE" in m.unsafe_patterns
    assert "SELECT *" in m.unsafe_patterns


def test_subquery_depth():
    """`subquery_depth` counts real SELECT-statement nesting via sqlparse.
    Three nested SELECTs -> depth 3.
    """
    sql = "SELECT * FROM (SELECT id FROM (SELECT id FROM users) t1) t2;"
    m = analyse_sql(sql)
    assert m.subquery_depth == 3


def test_no_subquery_with_nested_parens():
    """Nested parens that DO NOT contain SELECT must not inflate depth.

    Pins the bug in the previous paren-counting implementation:
    `SELECT (a + (b + c)) FROM t` had three levels of parens but zero
    nested subqueries, so the correct depth is 1.
    """
    m = analyse_sql("SELECT (a + (b + c)) FROM t")
    assert m.subquery_depth == 1


def test_three_level_subquery():
    """Three real SELECTs nested via IN (...) clauses -> depth 3."""
    sql = (
        "SELECT id FROM users WHERE x IN "
        "(SELECT y FROM t WHERE z IN (SELECT a FROM u))"
    )
    m = analyse_sql(sql)
    assert m.subquery_depth == 3


def test_unsafe_sql_subquery_depth():
    """UNSAFE_SQL fixture is three flat statements (UPDATE, DELETE, SELECT *) —
    no nested SELECTs, so depth is 1 (the top-level SELECT)."""
    m = analyse_sql(UNSAFE_SQL)
    assert m.subquery_depth == 1
