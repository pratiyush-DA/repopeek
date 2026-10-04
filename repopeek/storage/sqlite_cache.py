"""Optional derived SQLite traversal cache for fast recursive and multi-hop queries."""

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from repopeek.models.schema import CanonicalGraph


def build_sqlite_cache(graph: CanonicalGraph, db_path: Path) -> None:
    """Construct an indexed SQLite traversal cache from a CanonicalGraph."""
    db_file = Path(db_path).resolve()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    if db_file.exists():
        db_file.unlink()

    conn = sqlite3.connect(str(db_file))
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            PRAGMA synchronous = OFF;
            PRAGMA journal_mode = MEMORY;

            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                sig TEXT,
                file TEXT,
                start_line INTEGER,
                end_line INTEGER,
                complexity INTEGER,
                facts_json TEXT,
                story_json TEXT,
                content_hash TEXT NOT NULL
            );

            CREATE TABLE edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src TEXT NOT NULL,
                dst TEXT NOT NULL,
                type TEXT NOT NULL,
                confidence TEXT NOT NULL,
                how_derived TEXT
            );

            CREATE INDEX idx_edges_src ON edges(src, type);
            CREATE INDEX idx_edges_dst ON edges(dst, type);
            CREATE INDEX idx_nodes_kind ON nodes(kind);
            CREATE INDEX idx_nodes_file ON nodes(file);
            """
        )

        # Populate metadata
        meta_rows = [
            ("schema_version", graph.schema_version),
            ("tool_version", graph.tool_version),
            ("repo_commit", graph.repo_commit or ""),
            ("dirty", "1" if graph.dirty else "0"),
            ("nodes_count", str(len(graph.nodes))),
            ("edges_count", str(len(graph.edges))),
        ]
        cur.executemany("INSERT INTO metadata(key, value) VALUES (?, ?);", meta_rows)

        # Populate nodes
        node_rows = []
        for node in graph.nodes.values():
            node_rows.append(
                (
                    node.id,
                    node.kind,
                    node.sig,
                    node.span.file if node.span else None,
                    node.span.start if node.span else None,
                    node.span.end if node.span else None,
                    node.facts.complexity,
                    json.dumps(node.facts.model_dump(), sort_keys=True),
                    json.dumps(node.story.model_dump(), sort_keys=True) if node.story else None,
                    node.content_hash,
                )
            )
        cur.executemany(
            """
            INSERT INTO nodes(id, kind, sig, file, start_line, end_line, complexity, facts_json, story_json, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            node_rows,
        )

        # Populate edges
        edge_rows = []
        for edge in graph.edges:
            how_derived = edge.evidence.how_derived if edge.evidence else None
            edge_rows.append(
                (
                    edge.src,
                    edge.dst,
                    edge.type.value,
                    edge.confidence.value,
                    how_derived,
                )
            )
        cur.executemany(
            """
            INSERT INTO edges(src, dst, type, confidence, how_derived)
            VALUES (?, ?, ?, ?, ?);
            """,
            edge_rows,
        )

        conn.commit()
    finally:
        conn.close()


def query_sqlite_impact(
    db_path: Path,
    target_id: str,
    max_depth: int = 5,
) -> List[Dict[str, Any]]:
    """Compute upstream impact tree using recursive Common Table Expressions (CTE)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        query = """
        WITH RECURSIVE impact_tree(src, dst, type, depth) AS (
            SELECT src, dst, type, 1
            FROM edges
            WHERE dst = ?
            UNION
            SELECT e.src, e.dst, e.type, it.depth + 1
            FROM edges e
            JOIN impact_tree it ON e.dst = it.src
            WHERE it.depth < ?
        )
        SELECT DISTINCT it.src, it.dst, it.type, it.depth, n.kind, n.file
        FROM impact_tree it
        LEFT JOIN nodes n ON it.src = n.id
        ORDER BY it.depth ASC;
        """
        rows = cur.execute(query, (target_id, max_depth)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_sqlite_nodes(
    db_path: Path,
    kind: Optional[str] = None,
    file: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query nodes matching kind or file constraints from SQLite cache."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        clauses = []
        params = []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if file:
            clauses.append("file = ?")
            params.append(file)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = cur.execute(f"SELECT * FROM nodes {where} ORDER BY id ASC;", params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_sqlite_edges(
    db_path: Path,
    src: Optional[str] = None,
    dst: Optional[str] = None,
    edge_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query edges matching endpoints or relationship type from SQLite cache."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        clauses = []
        params = []
        if src:
            clauses.append("src = ?")
            params.append(src)
        if dst:
            clauses.append("dst = ?")
            params.append(dst)
        if edge_type:
            clauses.append("type = ?")
            params.append(edge_type)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = cur.execute(f"SELECT * FROM edges {where} ORDER BY id ASC;", params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_sqlite_file(file_path: Any, graph: CanonicalGraph, db_path: Path) -> None:
    """Incrementally upsert nodes and edges for a single file into SQLite cache in <15ms."""
    db_file = Path(db_path).resolve()
    if not db_file.exists():
        return

    fpath = str(file_path).replace("\\", "/")
    conn = sqlite3.connect(str(db_file))
    try:
        cur = conn.cursor()
        fname = Path(fpath).name
        cur.execute("SELECT id FROM nodes WHERE file = ? OR file LIKE ?", (fpath, f"%{fname}"))
        old_ids = [r[0] for r in cur.fetchall()]

        cur.execute("DELETE FROM nodes WHERE file = ? OR file LIKE ?", (fpath, f"%{fname}"))
        for oid in old_ids:
            cur.execute("DELETE FROM edges WHERE src = ? OR dst = ?", (oid, oid))

        file_nodes = [
            n for n in graph.nodes.values()
            if n.span and (
                n.span.file.replace("\\", "/") == fpath
                or n.span.file.replace("\\", "/").endswith(fpath)
                or fpath.endswith(n.span.file.replace("\\", "/"))
            )
        ]
        node_tuples = [
            (
                node.id,
                node.kind,
                node.sig,
                node.span.file if node.span else None,
                node.span.start if node.span else None,
                node.span.end if node.span else None,
                node.facts.complexity,
                json.dumps(node.facts.model_dump(exclude_none=True)),
                json.dumps(node.story.model_dump(exclude_none=True)) if node.story else None,
                node.content_hash,
            )
            for node in file_nodes
        ]
        cur.executemany(
            """
            INSERT OR REPLACE INTO nodes
            (id, kind, sig, file, start_line, end_line, complexity, facts_json, story_json, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            node_tuples,
        )

        file_node_ids = {n.id for n in file_nodes}
        file_edges = [
            e for e in graph.edges
            if e.src in file_node_ids or e.dst in file_node_ids
        ]
        edge_tuples = [
            (
                edge.src,
                edge.dst,
                edge.type.value if hasattr(edge.type, "value") else str(edge.type),
                edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence),
                edge.evidence.how_derived if edge.evidence else None,
            )
            for edge in file_edges
        ]
        cur.executemany(
            """
            INSERT INTO edges (src, dst, type, confidence, how_derived)
            VALUES (?, ?, ?, ?, ?);
            """,
            edge_tuples,
        )
        conn.commit()
    finally:
        conn.close()

