"""Focused unit tests for RepoPeek Polyglot Parsers (SQL, Shell, JSON, YAML)."""

from pathlib import Path
import pytest

from repopeek.models.schema import Confidence, EdgeType
from repopeek.parsers.config import JsonConfigParser, YamlConfigParser
from repopeek.parsers.shell import ShellParser
from repopeek.parsers.sql import SqlParser


# ---------------------------------------------------------------------------
# SQL Parser Tests
# ---------------------------------------------------------------------------

def test_sql_parser_oracle_and_table_defs():
    sql = """CREATE TABLE accounts (
    account_id NUMBER PRIMARY KEY,
    owner_name VARCHAR2(100) NOT NULL,
    balance NUMBER(12, 2) DEFAULT 0.00
);"""
    parser = SqlParser(default_dialect="oracle")
    res = parser.parse_source(sql, rel_path="db/schema.sql")
    assert res.is_success
    assert res.language == "sql"

    # Verify table definition node
    table_node = next(n for n in res.nodes if n.kind == "sql_table")
    assert table_node.id == "sql:db/schema.sql::table.accounts"
    assert "CREATE TABLE accounts" in table_node.sig
    assert table_node.facts.params == ["account_id", "owner_name", "balance"]
    assert table_node.facts.writes == ["accounts"]

    # Verify DEFINED_IN edge
    edge = next(e for e in res.edges if e.type == EdgeType.DEFINED_IN)
    assert edge.src == table_node.id
    assert edge.dst == "sql:db/schema.sql::<file>"


def test_sql_parser_select_query_and_references():
    sql = """SELECT a.account_id, a.owner_name, t.amount
FROM accounts a
JOIN transactions t ON a.account_id = t.account_id
WHERE t.status = 'COMPLETED';"""
    parser = SqlParser(default_dialect="oracle")
    res = parser.parse_source(sql, rel_path="db/queries.sql")
    assert res.is_success

    stmt_node = next(n for n in res.nodes if n.kind == "sql_query")
    assert "SELECT" in stmt_node.sig
    assert "accounts" in stmt_node.facts.reads
    assert "transactions" in stmt_node.facts.reads
    assert "account_id" in stmt_node.facts.reads
    assert "amount" in stmt_node.facts.reads

    # Verify READS edges for referenced tables
    table_reads = [e.dst for e in res.edges if e.type == EdgeType.READS]
    assert "accounts" in table_reads
    assert "transactions" in table_reads


def test_sql_parser_dialect_fallback():
    # Postgres specific syntax (e.g. SERIAL, RETURNING)
    sql = "INSERT INTO events (name) VALUES ('login') RETURNING id;"
    parser = SqlParser(default_dialect="oracle")
    res = parser.parse_source(sql, rel_path="db/insert.sql")
    assert res.is_success
    stmt = next(n for n in res.nodes if n.kind == "sql_query")
    assert "INSERT INTO events" in stmt.sig
    assert "events" in stmt.facts.writes


def test_sql_parser_malformed_resilience():
    sql = "CREATE TABLE broken (;;; SELECT invalid FROM;"
    parser = SqlParser(default_dialect="oracle")
    res = parser.parse_source(sql, rel_path="db/broken.sql")

    assert not res.is_success
    assert len(res.errors) > 0
    # Fallback regex must recover table.broken
    table_node = next((n for n in res.nodes if n.id == "sql:db/broken.sql::table.broken"), None)
    assert table_node is not None
    assert table_node.story.confidence == "unresolved"


# ---------------------------------------------------------------------------
# Shell Parser Tests
# ---------------------------------------------------------------------------

def test_shell_parser_commands_and_scripts():
    script = """#!/usr/bin/env bash
set -e
echo "Starting test suite..."
python tests/run_tests.py --verbose | grep -E "PASS|FAIL"
bash deploy.sh
"""
    parser = ShellParser()
    res = parser.parse_source(script, rel_path="scripts/test.sh")
    assert res.is_success
    assert res.language == "shell"

    commands = [n.sig for n in res.nodes if n.kind == "command"]
    assert any("python tests/run_tests.py" in c for c in commands)
    assert any("grep" in c for c in commands)

    # Verify RUNS_SCRIPT edges
    script_targets = [e.dst for e in res.edges if e.type == EdgeType.RUNS_SCRIPT]
    assert "tests/run_tests.py" in script_targets
    assert "deploy.sh" in script_targets


def test_shell_parser_env_variables():
    script = """export API_KEY="secret_key"
DB_HOST="localhost"
curl -H "Authorization: $API_KEY" http://${DB_HOST}:8080/health
"""
    parser = ShellParser()
    res = parser.parse_source(script, rel_path="scripts/api.sh")
    assert res.is_success

    file_node = next(n for n in res.nodes if n.kind == "file")
    assert "API_KEY" in file_node.facts.writes
    assert "DB_HOST" in file_node.facts.writes
    assert "API_KEY" in file_node.facts.reads
    assert "DB_HOST" in file_node.facts.reads

    writes_edges = [e.dst for e in res.edges if e.type == EdgeType.WRITES]
    assert "API_KEY" in writes_edges
    assert "DB_HOST" in writes_edges


# ---------------------------------------------------------------------------
# JSON & YAML Configuration Parser Tests
# ---------------------------------------------------------------------------

def test_json_parser_nested_and_keys():
    content = """{
  "service": "billing",
  "port": 9000,
  "database": {
    "host": "localhost",
    "pool": 10
  }
}"""
    parser = JsonConfigParser()
    res = parser.parse_source(content, rel_path="config/app.json")
    assert res.is_success
    assert res.language == "json"

    node_ids = {n.id for n in res.nodes}
    assert "json:config/app.json::service" in node_ids
    assert "json:config/app.json::database.host" in node_ids
    assert "json:config/app.json::database.pool" in node_ids

    # Verify DEFINED_IN edge
    edges = [e for e in res.edges if e.src == "json:config/app.json::database.host"]
    assert len(edges) == 1
    assert edges[0].dst == "json:config/app.json::<config>"


def test_json_parser_malformed_resilience():
    content = '{ "service": "billing", broken_json: '
    parser = JsonConfigParser()
    res = parser.parse_source(content, rel_path="config/broken.json")
    assert not res.is_success
    assert len(res.errors) == 1
    assert "JSONDecodeError" in res.errors[0]
    file_node = next(n for n in res.nodes if n.kind == "file")
    assert file_node.story.confidence == "unresolved"


def test_yaml_parser_nested_and_script_targets():
    content = """pipeline:
  name: nightly_build
  entrypoint: scripts/build.sh
  env: production
"""
    parser = YamlConfigParser()
    res = parser.parse_source(content, rel_path="config/build.yaml")
    assert res.is_success
    assert res.language == "yaml"

    node_ids = {n.id for n in res.nodes}
    assert "yaml:config/build.yaml::pipeline.name" in node_ids
    assert "yaml:config/build.yaml::pipeline.entrypoint" in node_ids

    # Verify script execution target detection
    script_edges = [e for e in res.edges if e.type == EdgeType.RUNS_SCRIPT]
    assert len(script_edges) == 1
    assert script_edges[0].dst == "scripts/build.sh"


def test_yaml_parser_malformed_resilience():
    content = """pipeline: [unclosed list
  bad indentation:
"""
    parser = YamlConfigParser()
    res = parser.parse_source(content, rel_path="config/broken.yaml")
    assert not res.is_success
    assert len(res.errors) == 1
    assert "YAMLError" in res.errors[0]
    file_node = next(n for n in res.nodes if n.kind == "file")
    assert file_node.story.confidence == "unresolved"


def test_sql_create_function_not_mislabeled_as_table():
    """CREATE FUNCTION must be a function node; EXTENSION/GRANT must not become tables.

    Regression: exp.Create was always routed to the table extractor, so
    CREATE OR REPLACE FUNCTION fix_timezone_setting() surfaced as a sql_table
    (the graph lying about the schema).
    """
    sql = """CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
GRANT ALL PRIVILEGES ON DATABASE app_db TO app_user;
CREATE OR REPLACE FUNCTION fix_timezone_setting()
RETURNS void AS $$
BEGIN
    SET timezone = 'UTC';
END;
$$ LANGUAGE plpgsql;"""
    res = SqlParser().parse_source(sql, rel_path="postgres/init.sql")

    fn = next((n for n in res.nodes if "fix_timezone_setting" in n.id), None)
    assert fn is not None
    assert fn.kind == "sql_query"
    assert "function.fix_timezone_setting" in fn.id
    assert "CREATE FUNCTION" in fn.sig
    # Nothing in this script is a real table, so no sql_table node should exist.
    assert not any(n.kind == "sql_table" for n in res.nodes)


def test_sql_real_create_table_still_sql_table():
    """A genuine CREATE TABLE must still produce a sql_table node with columns."""
    sql = "CREATE TABLE accounts (id INT PRIMARY KEY, owner VARCHAR(100));"
    res = SqlParser(default_dialect="postgres").parse_source(sql, rel_path="db/schema.sql")
    table = next((n for n in res.nodes if n.kind == "sql_table"), None)
    assert table is not None
    assert "table.accounts" in table.id
    assert table.facts.writes == ["accounts"]
