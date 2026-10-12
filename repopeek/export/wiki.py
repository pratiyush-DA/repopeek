"""Wikipedia-style Markdown agent wiki exporter for repository knowledge graphs.

Generates an agent-crawlable wiki in `wiki/`:
- `wiki/index.md` (master index & catalog)
- `wiki/community_<id>_<slug>.md` (per-community articles)
- `wiki/god_<slug>.md` (deep-dive articles on core architectural hubs)
All articles use standard relative Markdown links for seamless agent traversal.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from repopeek.graph.analysis import god_nodes
from repopeek.graph.clustering import compute_cohesion_scores, detect_communities, generate_community_labels
from repopeek.models.schema import CanonicalGraph, NodeCard

_UNSAFE_SLUG_CHARS = re.compile(r'[<>:"/\\|?*#%\x00-\x1f\x7f\s]')


def _safe_slug(name: str, limit: int = 80) -> str:
    """Create a filesystem- and Markdown-safe slug."""
    s = name.replace("/", "-").replace("\\", "-").replace("::", "-")
    s = s.replace("(", "").replace(")", "").replace(".", "-")
    s = _UNSAFE_SLUG_CHARS.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("._- ")
    return (s[:limit] if s else "unnamed").lower()


def _get_display_name(card: Optional[NodeCard], nid: str) -> str:
    if card and card.sig:
        return card.sig
    if card and card.id:
        return card.id.split("::")[-1]
    return nid.split("::")[-1] if "::" in nid else nid


def export_wiki(
    graph: CanonicalGraph,
    out_dir: Path,
    communities: Optional[Dict[int, List[str]]] = None,
    community_labels: Optional[Dict[int, str]] = None,
    cohesion_scores: Optional[Dict[int, float]] = None,
) -> int:
    """Generate complete agent wiki under out_dir. Returns number of articles created."""
    wiki_path = Path(out_dir).resolve()
    wiki_path.mkdir(parents=True, exist_ok=True)

    if communities is None:
        communities = detect_communities(graph)
    if cohesion_scores is None:
        cohesion_scores = compute_cohesion_scores(graph, communities)
    if community_labels is None:
        community_labels = generate_community_labels(graph, communities)

    gods_data = god_nodes(graph, top_n=10)

    # Invert node to community
    node_to_comm: Dict[str, int] = {}
    for cid, member_ids in communities.items():
        for mid in member_ids:
            node_to_comm[mid] = cid

    # Pre-compute community slugs
    comm_slugs: Dict[int, str] = {}
    used_slugs: Set[str] = {"index"}

    def _unique_slug(base: str) -> str:
        candidate = base
        count = 2
        while candidate in used_slugs:
            candidate = f"{base}_{count}"
            count += 1
        used_slugs.add(candidate)
        return candidate

    for cid, label in community_labels.items():
        slug_base = f"community_{cid}_{_safe_slug(label)}"
        comm_slugs[cid] = _unique_slug(slug_base)

    # Pre-compute god node slugs
    god_slugs: Dict[str, str] = {}
    for g in gods_data:
        nid = g["id"]
        lbl = g["label"]
        slug_base = f"god_{_safe_slug(lbl)}"
        god_slugs[nid] = _unique_slug(slug_base)

    article_count = 0

    # 1. Render Community Articles
    for cid, member_ids in communities.items():
        label = community_labels.get(cid, f"Community {cid}")
        slug = comm_slugs[cid]
        cscore = cohesion_scores.get(cid, 0.0)

        # Cross-community connections
        cross_counts: Dict[int, int] = {}
        for mid in member_ids:
            for out_edge in graph.out_edges(mid):
                other_comm = node_to_comm.get(out_edge.dst)
                if other_comm is not None and other_comm != cid:
                    cross_counts[other_comm] = cross_counts.get(other_comm, 0) + 1
            for in_edge in graph.in_edges(mid):
                other_comm = node_to_comm.get(in_edge.src)
                if other_comm is not None and other_comm != cid:
                    cross_counts[other_comm] = cross_counts.get(other_comm, 0) + 1

        lines = [
            f"# Community {cid}: {label}",
            f"> Cohesion Score: **{cscore:.2f}** | Members: **{len(member_ids)} code entities**",
            "",
            "## Architecture & Overview",
            f"This functional community encapsulates modular components primarily associated with `{label}`.",
            "",
            "## Key Code Entities (Members)",
            "| Symbol | Kind | File Citation | Hub Link |",
            "| :--- | :--- | :--- | :--- |",
        ]

        # Top member nodes
        for mid in member_ids[:30]:
            card = graph.get_node(mid)
            disp = _get_display_name(card, mid)
            knd = card.kind if card else "symbol"
            fl = f"`{card.span.file}:{card.span.start}`" if card and card.span and card.span.file else "internal"
            hub_link = f"[[god_{god_slugs[mid]}.md|Deep Dive]]" if mid in god_slugs else "-"
            lines.append(f"| `{disp}` | {knd} | {fl} | {hub_link} |")

        lines.extend([
            "",
            "## Cross-Community Interactions",
            "Interactions with neighboring functional clusters in the architecture:",
            "",
        ])

        if cross_counts:
            lines.append("| Target Community | Coupling Strength (Edges) | Article Link |")
            lines.append("| :--- | :--- | :--- |")
            for other_cid, cnt in sorted(cross_counts.items(), key=lambda x: x[1], reverse=True):
                other_lbl = community_labels.get(other_cid, f"Community {other_cid}")
                other_link = f"[{other_lbl}]({comm_slugs.get(other_cid, 'index')}.md)"
                lines.append(f"| {other_link} | **{cnt}** edges | [View Article]({comm_slugs.get(other_cid, 'index')}.md) |")
        else:
            lines.append("*This cluster operates with zero external cross-community couplings (completely decoupled).*")

        lines.extend([
            "",
            "---",
            "[⬅ Back to Index](index.md)",
        ])

        (wiki_path / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")
        article_count += 1

    # 2. Render God Node Articles
    for g in gods_data:
        nid = g["id"]
        lbl = g["label"]
        slug = god_slugs[nid]
        card = graph.get_node(nid)
        cid = node_to_comm.get(nid)
        comm_name = community_labels.get(cid, "Unassigned") if cid is not None else "None"
        comm_link = f"[{comm_name}]({comm_slugs.get(cid, 'index')}.md)" if cid is not None else "None"

        in_edges = graph.in_edges(nid)
        out_edges = graph.out_edges(nid)

        lines = [
            f"# God Node Deep Dive: `{lbl}`",
            f"> Centrality Degree: **{g['degree']}** (In: {g['in_degree']}, Out: {g['out_degree']}) | Kind: `{g['kind']}`",
            "",
            "## Context & Impact",
            f"- **File Location:** `{g['file']}:{g['start_line']}`",
            f"- **Functional Community:** {comm_link}",
            f"- **Complexity Score:** {g['complexity']}",
            "",
            "## Inbound Dependencies (Callers / Consumers)",
            f"There are **{len(in_edges)}** incoming edges directed at `{lbl}`. Modifying this symbol carries high blast radius:",
            "",
        ]

        if in_edges:
            lines.append("| Source Entity | Relation | Confidence |")
            lines.append("| :--- | :--- | :--- |")
            for e in in_edges[:20]:
                src_card = graph.get_node(e.src)
                src_lbl = _get_display_name(src_card, e.src)
                lines.append(f"| `{src_lbl}` | {e.type.value} | {e.confidence.value} |")
        else:
            lines.append("*No inbound edges recorded.*")

        lines.extend([
            "",
            "## Outbound Invocations (Downstream)",
            f"`{lbl}` invokes or depends upon **{len(out_edges)}** outgoing entities:",
            "",
        ])

        if out_edges:
            lines.append("| Destination Entity | Relation | Confidence |")
            lines.append("| :--- | :--- | :--- |")
            for e in out_edges[:20]:
                dst_card = graph.get_node(e.dst)
                dst_lbl = _get_display_name(dst_card, e.dst)
                lines.append(f"| `{dst_lbl}` | {e.type.value} | {e.confidence.value} |")
        else:
            lines.append("*No outbound edges recorded.*")

        lines.extend([
            "",
            "---",
            "[⬅ Back to Index](index.md)",
        ])

        (wiki_path / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")
        article_count += 1

    # 3. Render Master Index (`index.md`)
    index_lines = [
        "# Repository Architecture Wiki",
        "> Wikipedia-style knowledge graph documentation for human engineers and autonomous coding agents.",
        "",
        "## Summary Metrics",
        f"- **Total Code Symbols:** {len(graph.nodes)}",
        f"- **Total Relational Edges:** {len(graph.edges)}",
        f"- **Modular Communities:** {len(communities)}",
        f"- **Architectural Hubs (God Nodes):** {len(gods_data)}",
        "",
        "## Functional Communities (Modules)",
        "Click any community to inspect its components, dependencies, and boundary couplings:",
        "",
        "| ID | Community Article | Size | Cohesion |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for cid in sorted(communities.keys()):
        label = community_labels.get(cid, f"Community {cid}")
        slug = comm_slugs[cid]
        cscore = cohesion_scores.get(cid, 0.0)
        index_lines.append(f"| #{cid} | [{label}]({slug}.md) | {len(communities[cid])} entities | {cscore:.2f} |")

    index_lines.extend([
        "",
        "## Architectural Hubs (God Nodes)",
        "High-centrality symbols with extensive architectural reach:",
        "",
        "| Rank | Hub Symbol | Degree | File Citation | Article |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    for i, g in enumerate(gods_data, 1):
        nid = g["id"]
        lbl = g["label"]
        deg = g["degree"]
        fl = f"`{g['file']}:{g['start_line']}`" if g["file"] else "internal"
        slug = god_slugs.get(nid, "index")
        index_lines.append(f"| {i} | `{lbl}` | **{deg}** | {fl} | [Deep Dive]({slug}.md) |")

    index_lines.extend([
        "",
        "---",
        "*Generated by RepoPeek Polyglot Intelligence Engine.*",
    ])

    (wiki_path / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    article_count += 1

    return article_count
