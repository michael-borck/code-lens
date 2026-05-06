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
    m = analyse_sql(UNSAFE_SQL)
    assert len(m.unsafe_patterns) > 0
    patterns_str = " ".join(m.unsafe_patterns)
    assert "UPDATE" in patterns_str or "DELETE" in patterns_str or "SELECT *" in patterns_str


def test_subquery_depth():
    sql = "SELECT * FROM (SELECT id FROM (SELECT id FROM users) t1) t2;"
    m = analyse_sql(sql)
    assert m.subquery_depth >= 2
