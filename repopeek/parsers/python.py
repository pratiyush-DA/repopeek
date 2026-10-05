"""Deterministic Python AST and syntactic parser for RepoPeek."""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import sqlglot
from sqlglot import exp

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

SQL_KEYWORD_PATTERN = re.compile(
    r"(?i)\b(SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+.+\s+SET|DELETE\s+FROM|MERGE\s+INTO|CREATE\s+TABLE|ALTER\s+TABLE)\b"
)

FALLBACK_FUNC_RE = re.compile(
    r"^\s*(?P<async>async\s+)?def\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\((?P<args>.*?)(?:\)|:|$)"
)
FALLBACK_CLASS_RE = re.compile(
    r"^\s*class\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)(?:\((?P<bases>.*?)\))?\s*:"
)
FALLBACK_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(?P<mod>[a-zA-Z0-9_\.]+)\s+import\s+(?P<from_targets>[^#\n]+)|import\s+(?P<import_targets>[^#\n]+))"
)


class PythonParser(BaseParser):
    """Parses Python source code into canonical NodeCards and typed Edges."""

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse Python source code via AST with resilient syntax-error fallback."""
        norm_path = Path(rel_path).as_posix().lstrip("./")
        source_lines = source.splitlines()
        total_lines = max(1, len(source_lines))

        try:
            tree = ast.parse(source, filename=norm_path)
            return self._parse_ast(
                tree=tree,
                source=source,
                source_lines=source_lines,
                rel_path=norm_path,
                repo_root=repo_root,
            )
        except SyntaxError as exc:
            return self._parse_fallback(
                source=source,
                source_lines=source_lines,
                rel_path=norm_path,
                syntax_error=exc,
                repo_root=repo_root,
            )

    def _parse_ast(
        self,
        tree: ast.AST,
        source: str,
        source_lines: List[str],
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Extract canonical nodes and edges from valid Python AST."""
        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        total_lines = max(1, len(source_lines))

        file_id = NodeCard.make_id("py", rel_path, "<module>")
        module_doc = ast.get_docstring(tree)
        module_story_text = (
            module_doc.splitlines()[0].strip() if module_doc else f"Python module {rel_path}"
        )

        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"module {rel_path}",
            span=Span(file=rel_path, start=1, end=total_lines),
            facts=NodeFacts(),
            story=NodeStory(text=module_story_text, source="deterministic", confidence="high"),
            content_hash=hash_content(source),
        )
        nodes.append(file_node)

        # Process top-level imports
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target_name = alias.name
                    edges.append(
                        Edge(
                            src=file_id,
                            dst=target_name,
                            type=EdgeType.IMPORTS,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=rel_path,
                                start_line=node.lineno,
                                end_line=getattr(node, "end_lineno", node.lineno),
                                how_derived="ast_import",
                            ),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    target_name = f"{mod}.{alias.name}" if mod else alias.name
                    edges.append(
                        Edge(
                            src=file_id,
                            dst=target_name,
                            type=EdgeType.IMPORTS,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=rel_path,
                                start_line=node.lineno,
                                end_line=getattr(node, "end_lineno", node.lineno),
                                how_derived="ast_import",
                            ),
                        )
                    )

        # Process classes, methods, and functions
        self._extract_definitions(
            parent_node=tree,
            parent_scope_id=file_id,
            scope_prefix="",
            rel_path=rel_path,
            source_lines=source_lines,
            nodes=nodes,
            edges=edges,
        )

        return ParseResult(
            file_path=Path(rel_path),
            rel_path=rel_path,
            language="python",
            nodes=nodes,
            edges=edges,
            errors=[],
        )

    def _extract_definitions(
        self,
        parent_node: ast.AST,
        parent_scope_id: str,
        scope_prefix: str,
        rel_path: str,
        source_lines: List[str],
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Recursively process classes, functions, and nested scopes."""
        body = getattr(parent_node, "body", [])
        if not isinstance(body, list):
            return

        for child in body:
            if isinstance(child, ast.ClassDef):
                self._process_class(
                    cls_node=child,
                    parent_scope_id=parent_scope_id,
                    scope_prefix=scope_prefix,
                    rel_path=rel_path,
                    source_lines=source_lines,
                    nodes=nodes,
                    edges=edges,
                )
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(
                    fn_node=child,
                    parent_scope_id=parent_scope_id,
                    scope_prefix=scope_prefix,
                    rel_path=rel_path,
                    source_lines=source_lines,
                    nodes=nodes,
                    edges=edges,
                )
            elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                if not isinstance(parent_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._process_assignment(
                        assign_node=child,
                        parent_scope_id=parent_scope_id,
                        scope_prefix=scope_prefix,
                        rel_path=rel_path,
                        source_lines=source_lines,
                        nodes=nodes,
                        edges=edges,
                    )

    def _process_assignment(
        self,
        assign_node: ast.Assign | ast.AnnAssign,
        parent_scope_id: str,
        scope_prefix: str,
        rel_path: str,
        source_lines: List[str],
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Extract module-level and class-level variable definitions."""
        targets: List[ast.AST] = []
        if isinstance(assign_node, ast.Assign):
            targets = assign_node.targets
        else:
            targets = [assign_node.target]

        start_line = assign_node.lineno
        end_line = getattr(assign_node, "end_lineno", start_line)
        assign_source = "\n".join(source_lines[start_line - 1 : end_line]) if source_lines else ""

        for tgt in targets:
            name: Optional[str] = None
            if isinstance(tgt, ast.Name):
                name = tgt.id
            elif isinstance(tgt, ast.Attribute):
                name = ast.unparse(tgt)

            if not name:
                continue

            qualname = f"{scope_prefix}{name}"
            var_id = NodeCard.make_id("py", rel_path, qualname)

            sig = name
            if isinstance(assign_node, ast.AnnAssign) and assign_node.annotation:
                sig = f"{name}: {ast.unparse(assign_node.annotation)}"
            if assign_node.value:
                val_str = ast.unparse(assign_node.value)
                if len(val_str) > 40:
                    val_str = val_str[:37] + "..."
                sig = f"{sig} = {val_str}"

            card = NodeCard(
                id=var_id,
                kind="variable",
                sig=sig,
                span=Span(file=rel_path, start=start_line, end=end_line),
                facts=NodeFacts(),
                story=NodeStory(
                    text=f"Variable {qualname}",
                    source="deterministic",
                    confidence="high",
                ),
                content_hash=hash_content(assign_source or sig),
            )
            nodes.append(card)

            edges.append(
                Edge(
                    src=var_id,
                    dst=parent_scope_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=rel_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ast_assignment",
                    ),
                )
            )

    def _process_class(
        self,
        cls_node: ast.ClassDef,
        parent_scope_id: str,
        scope_prefix: str,
        rel_path: str,
        source_lines: List[str],
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Extract Class NodeCard, inheritance edges, and member methods."""
        qualname = f"{scope_prefix}{cls_node.name}"
        class_id = NodeCard.make_id("py", rel_path, qualname)
        start_line = cls_node.lineno
        end_line = getattr(cls_node, "end_lineno", start_line)

        # Bases
        bases = [ast.unparse(b) for b in cls_node.bases]
        bases_str = f"({', '.join(bases)})" if bases else ""
        sig = f"class {cls_node.name}{bases_str}"

        # Docstring and story
        cls_doc = ast.get_docstring(cls_node)
        if cls_doc:
            story_text = cls_doc.splitlines()[0].strip()
        elif bases:
            story_text = f"Class {cls_node.name} inheriting from {', '.join(bases)}"
        else:
            story_text = f"Class {cls_node.name}"

        # Source slice hash
        class_source = "\n".join(source_lines[start_line - 1 : end_line])

        card = NodeCard(
            id=class_id,
            kind="class",
            sig=sig,
            span=Span(file=rel_path, start=start_line, end=end_line),
            facts=NodeFacts(),
            story=NodeStory(text=story_text, source="deterministic", confidence="high"),
            content_hash=hash_content(class_source),
        )
        nodes.append(card)

        # DEFINED_IN edge
        edges.append(
            Edge(
                src=class_id,
                dst=parent_scope_id,
                type=EdgeType.DEFINED_IN,
                confidence=Confidence.RESOLVED,
                evidence=Evidence(
                    file=rel_path,
                    start_line=start_line,
                    end_line=end_line,
                    how_derived="ast_definition",
                ),
            )
        )

        # INHERITS edges
        for base in bases:
            edges.append(
                Edge(
                    src=class_id,
                    dst=base,
                    type=EdgeType.INHERITS,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=rel_path,
                        start_line=start_line,
                        end_line=start_line,
                        how_derived="ast_inheritance",
                    ),
                )
            )

        # Recurse for member methods and nested classes
        self._extract_definitions(
            parent_node=cls_node,
            parent_scope_id=class_id,
            scope_prefix=f"{qualname}.",
            rel_path=rel_path,
            source_lines=source_lines,
            nodes=nodes,
            edges=edges,
        )

    def _process_function(
        self,
        fn_node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_scope_id: str,
        scope_prefix: str,
        rel_path: str,
        source_lines: List[str],
        nodes: List[NodeCard],
        edges: List[Edge],
    ) -> None:
        """Extract Function/Method NodeCard, calls, reads, writes, and embedded SQL."""
        qualname = f"{scope_prefix}{fn_node.name}"
        func_id = NodeCard.make_id("py", rel_path, qualname)
        is_method = "." in scope_prefix
        kind = "method" if is_method else "function"

        start_line = fn_node.lineno
        end_line = getattr(fn_node, "end_lineno", start_line)

        # Signature
        async_prefix = "async " if isinstance(fn_node, ast.AsyncFunctionDef) else ""
        args_str = ast.unparse(fn_node.args)
        ret_str = f" -> {ast.unparse(fn_node.returns)}" if fn_node.returns else ""
        sig = f"{async_prefix}def {fn_node.name}({args_str}){ret_str}"

        # Parameter list
        params: List[str] = [arg.arg for arg in fn_node.args.posonlyargs + fn_node.args.args + fn_node.args.kwonlyargs]
        if fn_node.args.vararg:
            params.append(f"*{fn_node.args.vararg.arg}")
        if fn_node.args.kwarg:
            params.append(f"**{fn_node.args.kwarg.arg}")

        returns = ast.unparse(fn_node.returns) if fn_node.returns else None

        # Analyze function body metrics: complexity, calls, reads, writes, raises, embedded SQL, data flow
        facts, call_edges, raise_edges, sql_nodes, sql_edges, data_nodes, data_edges = self._analyze_function_body(
            fn_node=fn_node,
            func_id=func_id,
            parent_scope_id=parent_scope_id,
            scope_prefix=scope_prefix,
            rel_path=rel_path,
            params=params,
            returns=returns,
        )

        # Check for route decorators (FastAPI, Flask, Starlette, etc.)
        for dec in fn_node.decorator_list:
            if isinstance(dec, ast.Call) and dec.args:
                arg0 = dec.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    path_val = arg0.value
                    if path_val.startswith("/") or "/" in path_val:
                        if isinstance(dec.func, ast.Attribute):
                            attr = dec.func.attr.upper()
                            if attr in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                                facts.reads.append(f"ROUTE:{attr}:{path_val}")
                            elif attr == "ROUTE":
                                flask_methods = []
                                for kw in dec.keywords:
                                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                        for elt in kw.value.elts:
                                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                                flask_methods.append(elt.value.upper())
                                if flask_methods:
                                    for fm in flask_methods:
                                        facts.reads.append(f"ROUTE:{fm}:{path_val}")
                                else:
                                    facts.reads.append(f"ROUTE:GET:{path_val}")
                            else:
                                facts.reads.append(f"ROUTE:{m_name}:{path_val}")
                        else:
                            facts.reads.append(f"ROUTE:{m_name}:{path_val}")

        # Docstring and story
        fn_doc = ast.get_docstring(fn_node)
        if fn_doc:
            story_text = fn_doc.splitlines()[0].strip()
        else:
            param_repr = ", ".join(params) if params else "no arguments"
            story_text = f"{kind.capitalize()} {fn_node.name} taking ({param_repr})"

        func_source = "\n".join(source_lines[start_line - 1 : end_line])

        card = NodeCard(
            id=func_id,
            kind=kind,
            sig=sig,
            span=Span(file=rel_path, start=start_line, end=end_line),
            facts=facts,
            story=NodeStory(text=story_text, source="deterministic", confidence="high"),
            content_hash=hash_content(func_source),
        )
        nodes.append(card)

        # DEFINED_IN edge
        edges.append(
            Edge(
                src=func_id,
                dst=parent_scope_id,
                type=EdgeType.DEFINED_IN,
                confidence=Confidence.RESOLVED,
                evidence=Evidence(
                    file=rel_path,
                    start_line=start_line,
                    end_line=end_line,
                    how_derived="ast_definition",
                ),
            )
        )

        edges.extend(call_edges)
        edges.extend(raise_edges)
        nodes.extend(sql_nodes)
        edges.extend(sql_edges)
        nodes.extend(data_nodes)
        edges.extend(data_edges)

        # Process nested functions if any
        self._extract_definitions(
            parent_node=fn_node,
            parent_scope_id=func_id,
            scope_prefix=f"{qualname}.",
            rel_path=rel_path,
            source_lines=source_lines,
            nodes=nodes,
            edges=edges,
        )

    def _analyze_function_body(
        self,
        fn_node: ast.FunctionDef | ast.AsyncFunctionDef,
        func_id: str,
        parent_scope_id: str,
        scope_prefix: str,
        rel_path: str,
        params: List[str],
        returns: Optional[str],
    ) -> Tuple[NodeFacts, List[Edge], List[Edge], List[NodeCard], List[Edge], List[NodeCard], List[Edge]]:
        """Walk AST inside function to compute complexity, calls, data accesses, SQL, and data flow."""
        complexity = 1
        calls_count = 0
        reads: Set[str] = set()
        writes: Set[str] = set()
        raises: Set[str] = set()
        call_edges: List[Edge] = []
        raise_edges: List[Edge] = []
        sql_nodes: List[NodeCard] = []
        sql_edges: List[Edge] = []
        data_nodes: List[NodeCard] = []
        data_edges: List[Edge] = []
        created_attr_nodes: Set[str] = set()

        is_method = "." in scope_prefix
        class_name = scope_prefix.rstrip(".") if is_method else ""

        # Instance attribute discovery in __init__
        if fn_node.name == "__init__" and is_method:
            for stmt in fn_node.body:
                targets: List[ast.AST] = []
                if isinstance(stmt, ast.Assign):
                    targets = stmt.targets
                elif isinstance(stmt, ast.AnnAssign):
                    targets = [stmt.target]
                for tgt in targets:
                    if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                        attr_name = tgt.attr
                        var_qualname = f"{class_name}.{attr_name}"
                        var_id = NodeCard.make_id("py", rel_path, var_qualname)
                        if var_id not in created_attr_nodes:
                            created_attr_nodes.add(var_id)
                            sig = f"self.{attr_name}"
                            if isinstance(stmt, ast.AnnAssign) and stmt.annotation:
                                sig = f"self.{attr_name}: {ast.unparse(stmt.annotation)}"
                            if stmt.value:
                                val_repr = ast.unparse(stmt.value)
                                if len(val_repr) > 40:
                                    val_repr = val_repr[:37] + "..."
                                sig = f"{sig} = {val_repr}"
                            card = NodeCard(
                                id=var_id,
                                kind="variable",
                                sig=sig,
                                span=Span(
                                    file=rel_path,
                                    start=stmt.lineno,
                                    end=getattr(stmt, "end_lineno", stmt.lineno),
                                ),
                                facts=NodeFacts(),
                                story=NodeStory(
                                    text=f"Instance attribute {var_qualname}",
                                    source="deterministic",
                                    confidence="high",
                                ),
                                content_hash=hash_content(sig),
                            )
                            data_nodes.append(card)
                            data_edges.append(
                                Edge(
                                    src=var_id,
                                    dst=parent_scope_id,
                                    type=EdgeType.DEFINED_IN,
                                    confidence=Confidence.RESOLVED,
                                    evidence=Evidence(
                                        file=rel_path,
                                        start_line=stmt.lineno,
                                        end_line=getattr(stmt, "end_lineno", stmt.lineno),
                                        how_derived="ast_init_attribute",
                                    ),
                                )
                            )

        # Iterate all AST nodes inside function body
        for sub_node in ast.walk(fn_node):
            if sub_node is fn_node:
                continue

            # Cyclomatic complexity branch contributors
            if isinstance(
                sub_node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.AsyncFor,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                    ast.Assert,
                    ast.comprehension,
                ),
            ):
                complexity += 1
            elif isinstance(sub_node, ast.BoolOp):
                complexity += max(0, len(sub_node.values) - 1)

            # Function/Method Calls
            elif isinstance(sub_node, ast.Call):
                calls_count += 1
                callee_name = ast.unparse(sub_node.func)
                call_edges.append(
                    Edge(
                        src=func_id,
                        dst=callee_name,
                        type=EdgeType.CALLS,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=rel_path,
                            start_line=sub_node.lineno,
                            end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                            how_derived="ast_call",
                        ),
                    )
                )

                # Check for config/env reader calls (e.g. os.getenv, config.get)
                call_lower = callee_name.lower()
                if "getenv" in call_lower or (
                    call_lower.endswith(".get")
                    and any(
                        k in call_lower
                        for k in (
                            "environ",
                            "config",
                            "settings",
                            "cfg",
                            "options",
                            "conf",
                            "params",
                            "app_config",
                        )
                    )
                ):
                    if (
                        sub_node.args
                        and isinstance(sub_node.args[0], ast.Constant)
                        and isinstance(sub_node.args[0].value, str)
                    ):
                        key_str = sub_node.args[0].value
                        reads.add(key_str)
                        data_edges.append(
                            Edge(
                                src=func_id,
                                dst=key_str,
                                type=EdgeType.READS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sub_node.lineno,
                                    end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                                    how_derived="ast_config_read",
                                ),
                            )
                        )

            # Exception Raises
            elif isinstance(sub_node, ast.Raise):
                if sub_node.exc:
                    if isinstance(sub_node.exc, ast.Call):
                        exc_name = ast.unparse(sub_node.exc.func)
                    else:
                        exc_name = ast.unparse(sub_node.exc)
                    raises.add(exc_name)
                    raise_edges.append(
                        Edge(
                            src=func_id,
                            dst=exc_name,
                            type=EdgeType.RAISES,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=rel_path,
                                start_line=sub_node.lineno,
                                end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                                how_derived="ast_raise",
                            ),
                        )
                    )

            # Subscript reads (e.g. os.environ['VAR'], config['database.dialect'])
            elif isinstance(sub_node, ast.Subscript):
                val_repr = ast.unparse(sub_node.value).lower()
                if "environ" in val_repr or any(
                    k in val_repr for k in ("config", "settings", "cfg", "options", "conf")
                ):
                    if isinstance(sub_node.slice, ast.Constant) and isinstance(
                        sub_node.slice.value, str
                    ):
                        key_str = sub_node.slice.value
                        reads.add(key_str)
                        data_edges.append(
                            Edge(
                                src=func_id,
                                dst=key_str,
                                type=EdgeType.READS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sub_node.lineno,
                                    end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                                    how_derived="ast_config_read",
                                ),
                            )
                        )

            # Data Reads and Writes (Attributes and Variables)
            elif isinstance(sub_node, ast.Attribute):
                attr_name = ast.unparse(sub_node)
                if isinstance(sub_node.ctx, ast.Store):
                    writes.add(attr_name)
                    data_edges.append(
                        Edge(
                            src=func_id,
                            dst=attr_name,
                            type=EdgeType.WRITES,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=rel_path,
                                start_line=sub_node.lineno,
                                end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                                how_derived="ast_attr_write",
                            ),
                        )
                    )
                elif isinstance(sub_node.ctx, ast.Load):
                    reads.add(attr_name)
                    data_edges.append(
                        Edge(
                            src=func_id,
                            dst=attr_name,
                            type=EdgeType.READS,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=rel_path,
                                start_line=sub_node.lineno,
                                end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                                how_derived="ast_attr_read",
                            ),
                        )
                    )

            elif isinstance(sub_node, ast.Name):
                if isinstance(sub_node.ctx, ast.Store):
                    writes.add(sub_node.id)
                elif isinstance(sub_node.ctx, ast.Load):
                    reads.add(sub_node.id)
                    if sub_node.id in params and sub_node.id not in ("self", "cls"):
                        data_edges.append(
                            Edge(
                                src=func_id,
                                dst=sub_node.id,
                                type=EdgeType.READS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sub_node.lineno,
                                    end_line=getattr(sub_node, "end_lineno", sub_node.lineno),
                                    how_derived="ast_param_read",
                                ),
                            )
                        )

            # Embedded SQL Detection in String Literals
            elif isinstance(sub_node, ast.Constant) and isinstance(sub_node.value, str):
                val = sub_node.value.strip()
                if SQL_KEYWORD_PATTERN.search(val):
                    sql_line = sub_node.lineno
                    end_sql_line = getattr(sub_node, "end_lineno", sql_line)
                    sql_id = NodeCard.make_id("sql", rel_path, f"query_L{sql_line}")
                    preview = " ".join(val.split())
                    if len(preview) > 60:
                        preview = preview[:57] + "..."

                    # Extract referenced SQL tables
                    sql_reads: Set[str] = set()
                    sql_writes: Set[str] = set()
                    try:
                        for stmt in sqlglot.parse(val):
                            if stmt is None:
                                continue
                            for tbl in stmt.find_all(exp.Table):
                                if tbl.name:
                                    sql_reads.add(tbl.name.lower())
                            if isinstance(stmt, (exp.Insert, exp.Update, exp.Delete)):
                                tgt = next(stmt.find_all(exp.Table), None)
                                if tgt and tgt.name:
                                    sql_writes.add(tgt.name.lower())
                    except Exception:
                        for m in re.findall(
                            r"(?i)\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", val
                        ):
                            sql_reads.add(m.lower())
                        for m in re.findall(
                            r"(?i)\b(?:INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*)", val
                        ):
                            sql_writes.add(m.lower())

                    sql_card = NodeCard(
                        id=sql_id,
                        kind="sql_query",
                        sig=preview,
                        span=Span(file=rel_path, start=sql_line, end=end_sql_line),
                        facts=NodeFacts(
                            reads=sorted(list(sql_reads)),
                            writes=sorted(list(sql_writes)),
                        ),
                        story=NodeStory(
                            text=f"Embedded SQL query: {preview}",
                            source="deterministic",
                            confidence="high",
                        ),
                        content_hash=hash_content(val),
                    )
                    sql_nodes.append(sql_card)
                    sql_edges.append(
                        Edge(
                            src=func_id,
                            dst=sql_id,
                            type=EdgeType.EMBEDS_SQL,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=rel_path,
                                start_line=sql_line,
                                end_line=end_sql_line,
                                how_derived="ast_embedded_sql",
                            ),
                        )
                    )

                    for tbl in sorted(sql_reads):
                        reads.add(tbl)
                        sql_edges.append(
                            Edge(
                                src=sql_id,
                                dst=tbl,
                                type=EdgeType.READS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sql_line,
                                    end_line=end_sql_line,
                                    how_derived="embedded_sql_read",
                                ),
                            )
                        )
                        sql_edges.append(
                            Edge(
                                src=func_id,
                                dst=tbl,
                                type=EdgeType.READS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sql_line,
                                    end_line=end_sql_line,
                                    how_derived="embedded_sql_read",
                                ),
                            )
                        )

                    for tbl in sorted(sql_writes):
                        writes.add(tbl)
                        sql_edges.append(
                            Edge(
                                src=sql_id,
                                dst=tbl,
                                type=EdgeType.WRITES,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sql_line,
                                    end_line=end_sql_line,
                                    how_derived="embedded_sql_write",
                                ),
                            )
                        )
                        sql_edges.append(
                            Edge(
                                src=func_id,
                                dst=tbl,
                                type=EdgeType.WRITES,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=rel_path,
                                    start_line=sql_line,
                                    end_line=end_sql_line,
                                    how_derived="embedded_sql_write",
                                ),
                            )
                        )

        facts = NodeFacts(
            calls=calls_count,
            reads=sorted(list(reads)),
            writes=sorted(list(writes)),
            raises=sorted(list(raises)),
            complexity=complexity,
            params=params,
            returns=returns,
        )

        return facts, call_edges, raise_edges, sql_nodes, sql_edges, data_nodes, data_edges

    def _parse_fallback(
        self,
        source: str,
        source_lines: List[str],
        rel_path: str,
        syntax_error: SyntaxError,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Resilient fallback parser for files with syntax errors."""
        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        total_lines = max(1, len(source_lines))
        file_id = NodeCard.make_id("py", rel_path, "<module>")

        err_line = syntax_error.lineno or 1
        err_msg = syntax_error.msg or "syntax error"
        error_desc = f"SyntaxError at line {err_line}: {err_msg}"

        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"module {rel_path} (broken syntax)",
            span=Span(file=rel_path, start=1, end=total_lines),
            facts=NodeFacts(),
            story=NodeStory(
                text=f"Python file with syntax error at line {err_line}: {err_msg}",
                source="deterministic",
                confidence="unresolved",
            ),
            content_hash=hash_content(source),
        )
        nodes.append(file_node)

        # Syntactic line scanning to recover declared functions, classes, and imports
        for idx, line in enumerate(source_lines, start=1):
            # Fallback imports
            imp_match = FALLBACK_IMPORT_RE.match(line)
            if imp_match:
                if imp_match.group("import_targets"):
                    for target in imp_match.group("import_targets").split(","):
                        tgt = target.strip().split(" as ")[0]
                        if tgt:
                            edges.append(
                                Edge(
                                    src=file_id,
                                    dst=tgt,
                                    type=EdgeType.IMPORTS,
                                    confidence=Confidence.UNRESOLVED,
                                    evidence=Evidence(
                                        file=rel_path,
                                        start_line=idx,
                                        end_line=idx,
                                        how_derived="fallback_import_regex",
                                    ),
                                )
                            )
                elif imp_match.group("mod"):
                    mod = imp_match.group("mod").strip()
                    for target in imp_match.group("from_targets").split(","):
                        tgt = target.strip().split(" as ")[0]
                        if tgt:
                            edges.append(
                                Edge(
                                    src=file_id,
                                    dst=f"{mod}.{tgt}",
                                    type=EdgeType.IMPORTS,
                                    confidence=Confidence.UNRESOLVED,
                                    evidence=Evidence(
                                        file=rel_path,
                                        start_line=idx,
                                        end_line=idx,
                                        how_derived="fallback_import_regex",
                                    ),
                                )
                            )

            # Fallback classes
            cls_match = FALLBACK_CLASS_RE.match(line)
            if cls_match:
                cls_name = cls_match.group("name")
                bases_raw = cls_match.group("bases")
                bases = [b.strip() for b in bases_raw.split(",") if b.strip()] if bases_raw else []
                cls_id = NodeCard.make_id("py", rel_path, cls_name)
                card = NodeCard(
                    id=cls_id,
                    kind="class",
                    sig=f"class {cls_name}" + (f"({', '.join(bases)})" if bases else ""),
                    span=Span(file=rel_path, start=idx, end=idx),
                    facts=NodeFacts(),
                    story=NodeStory(
                        text=f"Recovered class {cls_name} via fallback parser",
                        source="deterministic",
                        confidence="unresolved",
                    ),
                    content_hash=hash_content(line),
                )
                nodes.append(card)
                edges.append(
                    Edge(
                        src=cls_id,
                        dst=file_id,
                        type=EdgeType.DEFINED_IN,
                        confidence=Confidence.UNRESOLVED,
                        evidence=Evidence(
                            file=rel_path,
                            start_line=idx,
                            end_line=idx,
                            how_derived="fallback_class_regex",
                        ),
                    )
                )

            # Fallback functions
            fn_match = FALLBACK_FUNC_RE.match(line)
            if fn_match:
                fn_name = fn_match.group("name")
                is_async = bool(fn_match.group("async"))
                fn_id = NodeCard.make_id("py", rel_path, fn_name)
                card = NodeCard(
                    id=fn_id,
                    kind="function",
                    sig=f"{'async ' if is_async else ''}def {fn_name}(...)",
                    span=Span(file=rel_path, start=idx, end=idx),
                    facts=NodeFacts(),
                    story=NodeStory(
                        text=f"Recovered function {fn_name} via fallback parser",
                        source="deterministic",
                        confidence="unresolved",
                    ),
                    content_hash=hash_content(line),
                )
                nodes.append(card)
                edges.append(
                    Edge(
                        src=fn_id,
                        dst=file_id,
                        type=EdgeType.DEFINED_IN,
                        confidence=Confidence.UNRESOLVED,
                        evidence=Evidence(
                            file=rel_path,
                            start_line=idx,
                            end_line=idx,
                            how_derived="fallback_func_regex",
                        ),
                    )
                )

        return ParseResult(
            file_path=Path(rel_path),
            rel_path=rel_path,
            language="python",
            nodes=nodes,
            edges=edges,
            errors=[error_desc],
        )
