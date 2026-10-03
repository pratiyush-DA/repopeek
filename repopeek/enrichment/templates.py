"""Deterministic rule-based story builder extracting stories directly from AST facts."""

from pathlib import Path
from typing import Optional

from repopeek.models.schema import NodeCard, NodeStory


class DeterministicStoryBuilder:
    """Builds verifiable, zero-cost semantic narratives directly from syntactic code facts."""

    @classmethod
    def build_story(cls, node: NodeCard) -> NodeStory:
        """Construct a high-confidence, non-hallucinated narrative from AST metadata."""
        sym = node.id.split("::")[-1] if "::" in node.id else node.id
        kind = node.kind.lower()

        # 1. Functions & Methods
        if kind in ("function", "method"):
            text = cls._build_function_narrative(node, sym)
        # 2. Classes
        elif kind == "class":
            text = f"Class '{sym}' encapsulating component state and behavior"
        # 3. SQL Tables
        elif "table" in kind or sym.startswith("table."):
            tbl_name = sym.replace("table.", "")
            text = f"Relational table '{tbl_name}' defining database schema entities"
        # 4. SQL Queries
        elif "query" in kind or "sql" in kind:
            reads_str = f" reading {', '.join(node.facts.reads)}" if node.facts.reads else ""
            writes_str = f" modifying {', '.join(node.facts.writes)}" if node.facts.writes else ""
            text = f"SQL statement in {sym}{reads_str}{writes_str}".strip()
        # 5. Shell Scripts
        elif "shell" in kind or "script" in kind:
            text = f"Shell script '{sym}' orchestrating process commands and script executions"
        # 6. Configurations
        elif "config" in kind:
            text = f"Configuration declarations in '{sym}'"
        # 7. Modules and Files
        elif kind in ("module", "file"):
            fpath = node.span.file if node.span and node.span.file else sym
            text = f"Module '{Path(fpath).name}' defining symbols and dependencies"
        else:
            text = f"Syntactic {kind} definition for '{sym}'"

        return NodeStory(
            text=text,
            source="deterministic",
            confidence="high",
        )

    @classmethod
    def _build_function_narrative(cls, node: NodeCard, sym: str) -> str:
        """Compose precise sentence for a function or method based on signature and facts."""
        params = node.facts.params
        ret = node.facts.returns
        reads = [r.split("::")[-1].replace("table.", "") for r in node.facts.reads]
        writes = [w.split("::")[-1].replace("table.", "") for w in node.facts.writes]

        parts = [f"Function '{sym}'"]

        if params:
            param_str = ", ".join(params[:3])
            parts.append(f"accepting ({param_str})")

        if reads:
            parts.append(f"reading {', '.join(reads[:2])}")
        if writes:
            parts.append(f"writing {', '.join(writes[:2])}")

        if ret:
            parts.append(f"returning {ret}")
        elif node.facts.calls > 0:
            parts.append(f"invoking {node.facts.calls} operation(s)")

        return " ".join(parts)
