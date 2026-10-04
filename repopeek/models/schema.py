"""Data models and schemas for RepoPeek canonical property graph."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field, model_validator


class Confidence(str, Enum):
    """Confidence level of graph entities and relational edges."""
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    DYNAMIC = "dynamic"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


class EdgeType(str, Enum):
    """Taxonomy of canonical graph edge relationships."""
    DEFINED_IN = "DEFINED_IN"
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    READS = "READS"
    WRITES = "WRITES"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    INVOKES = "INVOKES"
    RAISES = "RAISES"
    CATCHES = "CATCHES"
    TESTS_CODE = "TESTS_CODE"
    EMBEDS_SQL = "EMBEDS_SQL"
    RUNS_SCRIPT = "RUNS_SCRIPT"


class Span(BaseModel):
    """Code or file span with line boundaries."""
    file: str = Field(description="Repo-relative path of the source file")
    start: int = Field(ge=1, description="1-indexed starting line number")
    end: int = Field(ge=1, description="1-indexed ending line number")

    @model_validator(mode="after")
    def validate_span_order(self) -> "Span":
        if self.start > self.end:
            raise ValueError(f"start line ({self.start}) cannot exceed end line ({self.end})")
        return self


NodeSpan = Span


class NodeFacts(BaseModel):
    """Deterministic AST and syntactic facts extracted from code."""
    calls: int = Field(default=0, description="Total count of calls made by this node")
    reads: List[str] = Field(default_factory=list, description="Variables, tables, or attributes read")
    writes: List[str] = Field(default_factory=list, description="Variables, tables, or attributes mutated")
    raises: List[str] = Field(default_factory=list, description="Exceptions raised")
    complexity: int = Field(default=1, ge=1, description="Cyclomatic complexity score")
    params: List[str] = Field(default_factory=list, description="Parameter signatures")
    returns: Optional[str] = Field(default=None, description="Return type annotation or expression")


class NodeStory(BaseModel):
    """Natural language or templated narrative of the node's intent."""
    text: str = Field(description="One-line summary story")
    source: Literal["deterministic", "llm", "cached"] = Field(
        default="deterministic", description="Generation mechanism"
    )
    confidence: Literal["high", "medium", "low", "dynamic", "unresolved"] = Field(
        default="high", description="Certainty score of the narrative"
    )


class NodeProvenance(BaseModel):
    """Audit and origin metadata anchoring the node to git commits."""
    commit: Optional[str] = Field(default=None, description="Git commit SHA (HEAD)")
    tool_version: str = Field(default="0.1.0", description="RepoPeek version")
    story_model: str = Field(default="deterministic", description="Model tier or generator")
    prompt_version: str = Field(default="v1", description="Prompt template version")
    blob_sha: Optional[str] = Field(default=None, description="Git blob SHA for the file")


class NodeCard(BaseModel):
    """Atomic unit consumed by low-context agents (<80 tokens)."""
    id: str = Field(description="Stable URI: <lang>:<repo-rel-path>::<qualified.name>")
    kind: str = Field(
        description="Node kind: repository, file, module, class, function, method, sql_query, json_config, yaml_config, shell_script, business_process, story"
    )
    sig: Optional[str] = Field(default=None, description="Call signature or declaration")
    span: Optional[Span] = Field(default=None, description="Physical code boundary")
    facts: NodeFacts = Field(default_factory=NodeFacts, description="AST facts summary")
    story: Optional[NodeStory] = Field(default=None, description="One-line story")
    snippet: Optional[str] = Field(default=None, description="Target source code slice for zero-file-read edits")
    blast: Optional[Dict[str, int]] = Field(default=None, description="Precomputed 1-hop blast radius metrics")
    content_hash: str = Field(description="SHA-256 of normalized body or file content")
    provenance: Optional[NodeProvenance] = Field(default=None, description="Git provenance")

    @classmethod
    def make_id(cls, lang: str, repo_rel_path: str, qualified_name: str) -> str:
        """Construct standard stable node URI."""
        norm_path = Path(repo_rel_path).as_posix().lstrip("./")
        return f"{lang}:{norm_path}::{qualified_name}"


class Evidence(BaseModel):
    """Proof and location backing an extracted edge."""
    file: str = Field(description="Source file containing evidence")
    start_line: int = Field(ge=1, description="1-indexed line start")
    end_line: int = Field(ge=1, description="1-indexed line end")
    how_derived: str = Field(
        description="Mechanism: ast_call, ast_import, sql_table_ref, shell_pipe, heuristic"
    )


class Edge(BaseModel):
    """Typed relationship connecting two canonical nodes."""
    src: str = Field(description="Source node ID")
    dst: str = Field(description="Target node ID")
    type: EdgeType = Field(description="Relationship type")
    confidence: Confidence = Field(default=Confidence.RESOLVED, description="Resolution certainty")
    evidence: Optional[Evidence] = Field(default=None, description="Evidence backing this edge")
    provenance: Optional[NodeProvenance] = Field(default=None, description="Git provenance")


class CanonicalGraph(BaseModel):
    """The canonical repository property graph containing all nodes and edges."""
    schema_version: str = Field(default="1.0.0", description="Schema version")
    repo_commit: Optional[str] = Field(default=None, description="Git commit SHA")
    dirty: bool = Field(default=False, description="Uncommitted changes present")
    tool_version: str = Field(default="0.1.0", description="RepoPeek version")
    nodes: Dict[str, NodeCard] = Field(default_factory=dict, description="Map of node ID to NodeCard")
    edges: List[Edge] = Field(default_factory=list, description="List of directed edges")

    def add_node(self, node: NodeCard) -> None:
        """Add or update a node card."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge after verifying endpoints."""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[NodeCard]:
        """Lookup node card by ID."""
        return self.nodes.get(node_id)

    def out_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[Edge]:
        """Get outgoing edges from node."""
        return [
            e for e in self.edges
            if e.src == node_id and (edge_type is None or e.type == edge_type)
        ]

    def in_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[Edge]:
        """Get incoming edges into node."""
        return [
            e for e in self.edges
            if e.dst == node_id and (edge_type is None or e.type == edge_type)
        ]
