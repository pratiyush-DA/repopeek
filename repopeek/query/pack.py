"""ContextPack data structures and markdown serializers for low-context agents."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ContextPack:
    """Minimal, self-contained sub-graph payload designed for low-context AI coding agents."""
    targets: List[str]
    token_budget: int = 1500
    estimated_tokens: int = 0
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    affected_tables: List[str] = field(default_factory=list)

    @staticmethod
    def estimate_tokens_from_text(text: str) -> int:
        """Fast, robust token estimator (~1.3 tokens per word or ~4 chars per token)."""
        words = len(text.split())
        return max(int(words * 1.3), len(text) // 4)

    def to_markdown(self) -> str:
        """Format a token-efficient, clean Markdown prompt block."""
        target_str = ", ".join(self.targets)
        lines = [
            f"# RepoPeek Context Pack: {target_str}",
            f"*Estimated Tokens: ~{self.estimated_tokens} (Budget: {self.token_budget})*",
            "",
            "## Atomic Node Cards",
        ]

        for n in self.nodes:
            nid = n.get("id", "")
            kind = n.get("kind", "")
            span = n.get("span")
            span_str = f"{span['file']}:{span['start']}-{span['end']}" if span else "global"
            story = n.get("story", {}).get("text", "No narrative available.")
            sig = n.get("sig")
            facts = n.get("facts", {})

            lines.append(f"### `{nid}` ({kind}) [{span_str}]")
            if sig:
                lines.append(f"- **Signature:** `{sig}`")
            lines.append(f"- **Story:** {story}")

            fact_details = []
            if facts.get("calls"):
                fact_details.append(f"calls={facts['calls']}")
            if facts.get("reads"):
                fact_details.append(f"reads={facts['reads']}")
            if facts.get("writes"):
                fact_details.append(f"writes={facts['writes']}")
            if facts.get("returns"):
                fact_details.append(f"returns={facts['returns']}")
            if fact_details:
                lines.append(f"- **Facts:** {', '.join(fact_details)}")
            lines.append("")

        if self.relationships:
            lines.append("## Relational Edges")
            for r in self.relationships:
                src = r.get("src", "")
                dst = r.get("dst", "")
                etype = r.get("type", "")
                conf = r.get("confidence", "")
                lines.append(f"- `{src}` -> `{dst}` [{etype}] ({conf})")
            lines.append("")

        if self.affected_files or self.affected_tables:
            lines.append("## Blast Radius Summary")
            if self.affected_files:
                lines.append(f"- **Affected Files:** {', '.join(sorted(self.affected_files))}")
            if self.affected_tables:
                lines.append(f"- **Affected Tables:** {', '.join(sorted(self.affected_tables))}")
            lines.append("")

        return "\n".join(lines).strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert ContextPack to serializable dictionary."""
        return {
            "targets": self.targets,
            "token_budget": self.token_budget,
            "estimated_tokens": self.estimated_tokens,
            "nodes_count": len(self.nodes),
            "relationships_count": len(self.relationships),
            "nodes": self.nodes,
            "relationships": self.relationships,
            "affected_files": self.affected_files,
            "affected_tables": self.affected_tables,
        }
