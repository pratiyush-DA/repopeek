"""Deterministic SQL parser for Oracle, ANSI, and Postgres dialects using SQLGlot."""

import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from repopeek.discovery.hasher import hash_content
from repopeek.models.schema import (
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    NodeFacts,
    NodeStory,
    Span,
)
from repopeek.parsers.base import BaseParser, ParseResult


class SqlParser(BaseParser):
    """Parses SQL files into canonical tables, queries, and referenced entities."""

    def __init__(self, default_dialect: str = "oracle") -> None:
        self.default_dialect = default_dialect

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
        dialect: Optional[str] = None,
    ) -> ParseResult:
        """Parse SQL statements with fallback dialect handling and syntax resilience."""
        norm_path = Path(rel_path).as_posix().lstrip("./")
        source_lines = source.splitlines()
        total_lines = max(1, len(source_lines))
        active_dialect = dialect or self.default_dialect

        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        errors: List[str] = []

        file_id = NodeCard.make_id("sql", norm_path, "<file>")
        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"sql_script {norm_path} ({active_dialect})",
            span=Span(file=norm_path, start=1, end=total_lines),
            facts=NodeFacts(),
            story=NodeStory(
                text=f"SQL script {norm_path} in {active_dialect} dialect",
                source="deterministic",
                confidence="high",
            ),
            content_hash=hash_content(source),
        )
        nodes.append(file_node)

        # Attempt parsing with default dialect, then fallbacks
        expressions: List[exp.Expression] = []
        successful_dialect = active_dialect

        dialects_to_try = [active_dialect]
        if active_dialect != "postgres":
            dialects_to_try.append("postgres")
        if "" not in dialects_to_try:
            dialects_to_try.append("")

        for d in dialects_to_try:
            try:
                parsed = [stmt for stmt in sqlglot.parse(source, read=d) if stmt is not None]
                if parsed:
                    expressions = parsed
                    successful_dialect = d or "ansi"
                    break
            except ParseError as pe:
                if d == dialects_to_try[-1]:
                    errors.append(f"SQLGlot parse failure in {norm_path}: {pe}")

        if not expressions and errors:
            # Resilient fallback: regex extraction of table creates and queries
            self._fallback_extract(source_lines, norm_path, file_id, nodes, edges)
            file_node.story.confidence = "unresolved"
            return ParseResult(
                file_path=Path(norm_path),
                rel_path=norm_path,
                language="sql",
                nodes=nodes,
                edges=edges,
                errors=errors,
            )

        # Process structured SQL statements
        curr_line = 1
        for idx, expression in enumerate(expressions):
            stmt_sql = expression.sql(dialect=successful_dialect)
            start_line, end_line = self._find_statement_span(source_lines, stmt_sql, curr_line)
            curr_line = end_line + 1

            if isinstance(expression, exp.Create):
                self._process_create_table(
                    create_exp=expression,
                    rel_path=norm_path,
                    file_id=file_id,
                    start_line=start_line,
                    end_line=end_line,
                    nodes=nodes,
                    edges=edges,
                )
            else:
                self._process_query_statement(
                    expression=expression,
                    rel_path=norm_path,
                    file_id=file_id,
                    stmt_idx=idx + 1,
                    start_line=start_line,
                    end_line=end_line,
                    nodes=nodes,
                    edges=edges,
                )

        return ParseResult(
            file_path=Path(norm_path),
            rel_path=norm_path,
            language="sql",
            nodes=nodes,
            edges=edges,
            errors=errors,
        )

    def _process_create_table(
        self,
        create_exp: exp.Create,
        rel_path: str,
        file_id: str,
        start_line: int,
        end_line: int,
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Extract table definition node and columns."""
        table_node = next(create_exp.find_all(exp.Table), None)
        if table_node and table_node.name:
            table_name = table_node.name
        elif hasattr(create_exp.this, "name") and create_exp.this.name:
            table_name = create_exp.this.name
        else:
            table_name = "unknown_table"

        columns = [col.name for col in create_exp.find_all(exp.ColumnDef) if col.name]

        table_id = NodeCard.make_id("sql", rel_path, f"table.{table_name}")
        sig = f"CREATE TABLE {table_name} ({', '.join(columns)})"

        card = NodeCard(
            id=table_id,
            kind="sql_table",
            sig=sig,
            span=Span(file=rel_path, start=start_line, end=end_line),
            facts=NodeFacts(writes=[table_name], params=columns),
            story=NodeStory(
                text=f"Table {table_name} with columns: {', '.join(columns)}",
                source="deterministic",
                confidence="high",
            ),
            content_hash=hash_content(create_exp.sql()),
        )
        nodes.append(card)

        # DEFINED_IN edge
        edges.append(
            Edge(
                src=table_id,
                dst=file_id,
                type=EdgeType.DEFINED_IN,
                confidence=Confidence.RESOLVED,
                evidence=Evidence(
                    file=rel_path,
                    start_line=start_line,
                    end_line=end_line,
                    how_derived="sql_create_table",
                ),
            )
        )

    def _process_query_statement(
        self,
        expression: exp.Expression,
        rel_path: str,
        file_id: str,
        stmt_idx: int,
        start_line: int,
        end_line: int,
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Extract query statement, referenced tables, and referenced columns."""
        tables: List[str] = sorted(list({t.name for t in expression.find_all(exp.Table) if t.name}))
        columns: List[str] = sorted(list({c.name for c in expression.find_all(exp.Column) if c.name}))
        
        # Determine statement kind and writes
        key = expression.key.upper() if hasattr(expression, "key") else "QUERY"
        writes: List[str] = []
        if isinstance(expression, (exp.Insert, exp.Update, exp.Delete)):
            target_table = next(expression.find_all(exp.Table), None)
            if target_table and target_table.name:
                writes.append(target_table.name)

        stmt_id = NodeCard.make_id("sql", rel_path, f"stmt_L{start_line}")
        compact_sql = " ".join(expression.sql().split())
        sig = compact_sql[:80] + ("..." if len(compact_sql) > 80 else "")

        card = NodeCard(
            id=stmt_id,
            kind="sql_query",
            sig=sig,
            span=Span(file=rel_path, start=start_line, end=end_line),
            facts=NodeFacts(reads=tables + columns, writes=writes),
            story=NodeStory(
                text=f"{key} statement querying {', '.join(tables) or 'inline tables'}",
                source="deterministic",
                confidence="high",
            ),
            content_hash=hash_content(expression.sql()),
        )
        nodes.append(card)

        # DEFINED_IN edge
        edges.append(
            Edge(
                src=stmt_id,
                dst=file_id,
                type=EdgeType.DEFINED_IN,
                confidence=Confidence.RESOLVED,
                evidence=Evidence(
                    file=rel_path,
                    start_line=start_line,
                    end_line=end_line,
                    how_derived="sql_statement",
                ),
            )
        )

        # READS edges to referenced tables
        for table in tables:
            edges.append(
                Edge(
                    src=stmt_id,
                    dst=table,
                    type=EdgeType.READS,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=rel_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="sql_table_read",
                    ),
                )
            )

        # WRITES edges to modified tables
        for table in writes:
            edges.append(
                Edge(
                    src=stmt_id,
                    dst=table,
                    type=EdgeType.WRITES,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=rel_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="sql_table_write",
                    ),
                )
            )

    def _find_statement_span(
        self,
        source_lines: List[str],
        stmt_sql: str,
        search_start: int,
    ) -> Tuple[int, int]:
        """Approximate line span boundaries for a statement in source code."""
        first_token = stmt_sql.split()[0].upper() if stmt_sql.split() else ""
        start = search_start
        for i in range(search_start - 1, len(source_lines)):
            line_clean = source_lines[i].strip().upper()
            if not line_clean.startswith("--") and first_token in line_clean:
                start = i + 1
                break

        # Search for terminating semicolon or end of lines
        end = start
        for i in range(start - 1, len(source_lines)):
            if ";" in source_lines[i]:
                end = i + 1
                break
            end = i + 1
        return start, max(start, end)

    def _fallback_extract(
        self,
        source_lines: List[str],
        rel_path: str,
        file_id: str,
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Regex-based fallback extraction when full SQL parsing fails."""
        create_re = re.compile(r"(?i)^\s*CREATE\s+TABLE\s+([a-zA-Z0-9_]+)")
        query_re = re.compile(r"(?i)^\s*(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b")

        for idx, line in enumerate(source_lines, start=1):
            create_m = create_re.match(line)
            if create_m:
                tname = create_m.group(1)
                tid = NodeCard.make_id("sql", rel_path, f"table.{tname}")
                nodes.append(
                    NodeCard(
                        id=tid,
                        kind="sql_table",
                        sig=f"CREATE TABLE {tname}",
                        span=Span(file=rel_path, start=idx, end=idx),
                        facts=NodeFacts(writes=[tname]),
                        story=NodeStory(
                            text=f"Recovered table {tname} via fallback regex",
                            source="deterministic",
                            confidence="unresolved",
                        ),
                        content_hash=hash_content(line),
                    )
                )
                edges.append(
                    Edge(
                        src=tid,
                        dst=file_id,
                        type=EdgeType.DEFINED_IN,
                        confidence=Confidence.UNRESOLVED,
                        evidence=Evidence(file=rel_path, start_line=idx, end_line=idx, how_derived="fallback_sql_regex"),
                    )
                )
            elif query_re.match(line):
                qid = NodeCard.make_id("sql", rel_path, f"stmt_L{idx}")
                nodes.append(
                    NodeCard(
                        id=qid,
                        kind="sql_query",
                        sig=line.strip()[:60],
                        span=Span(file=rel_path, start=idx, end=idx),
                        facts=NodeFacts(),
                        story=NodeStory(
                            text="Recovered query via fallback regex",
                            source="deterministic",
                            confidence="unresolved",
                        ),
                        content_hash=hash_content(line),
                    )
                )
                edges.append(
                    Edge(
                        src=qid,
                        dst=file_id,
                        type=EdgeType.DEFINED_IN,
                        confidence=Confidence.UNRESOLVED,
                        evidence=Evidence(file=rel_path, start_line=idx, end_line=idx, how_derived="fallback_sql_regex"),
                    )
                )
