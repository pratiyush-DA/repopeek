"""Standalone interactive HTML graph visualizer exporter for RepoPeek."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from repopeek.graph.clustering import detect_communities, generate_community_labels
from repopeek.models.schema import CanonicalGraph

COMMUNITY_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
    "#2b5c8f", "#d97312", "#c93b3d", "#5c9d98", "#418537",
    "#d4b032", "#976188", "#e6848e", "#835c46", "#a19793",
]


def export_html(
    graph: CanonicalGraph,
    out_file: Path,
    communities: Optional[Dict[int, List[str]]] = None,
    community_labels: Optional[Dict[int, str]] = None,
    max_nodes: int = 4000,
) -> Path:
    """Generate self-contained interactive graph.html with search, community filters, and inspector."""
    out_path = Path(out_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if communities is None:
        communities = detect_communities(graph)
    if community_labels is None:
        community_labels = generate_community_labels(graph, communities)

    node_to_comm: Dict[str, int] = {}
    for cid, members in communities.items():
        for mid in members:
            node_to_comm[mid] = cid

    # Degree centrality
    degrees: Dict[str, int] = {nid: 0 for nid in graph.nodes}
    for e in graph.edges:
        degrees[e.src] = degrees.get(e.src, 0) + 1
        degrees[e.dst] = degrees.get(e.dst, 0) + 1

    max_deg = max(degrees.values(), default=1) or 1

    # Prepare nodes for vis.js
    vis_nodes: List[Dict[str, Any]] = []
    sorted_node_ids = sorted(graph.nodes.keys(), key=lambda nid: degrees.get(nid, 0), reverse=True)
    if len(sorted_node_ids) > max_nodes:
        sorted_node_ids = sorted_node_ids[:max_nodes]
    included_set = set(sorted_node_ids)

    for nid in sorted_node_ids:
        card = graph.nodes[nid]
        cid = node_to_comm.get(nid, 0)
        cname = community_labels.get(cid, f"Community {cid}")
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        deg = degrees.get(nid, 1)

        label = card.sig or nid.split("::")[-1]
        size = 10 + 26 * (deg / max_deg)

        vis_nodes.append({
            "id": nid,
            "label": label,
            "title": f"{label}\nKind: {card.kind}\nFile: {card.span.file if card.span else 'unknown'}\nDegree: {deg}\nCommunity: {cname}",
            "color": {
                "background": color,
                "border": "#ffffff" if deg > 10 else color,
                "highlight": {"background": "#ffffff", "border": color},
            },
            "size": round(size, 1),
            "community": cid,
            "community_name": cname,
            "kind": card.kind,
            "file": card.span.file if card.span else "",
            "degree": deg,
        })

    # Prepare edges for vis.js
    vis_edges: List[Dict[str, Any]] = []
    for e in graph.edges:
        if e.src in included_set and e.dst in included_set:
            vis_edges.append({
                "from": e.src,
                "to": e.dst,
                "label": e.type.value if hasattr(e.type, "value") else str(e.type),
                "arrows": "to",
                "color": {"color": "rgba(180, 190, 210, 0.35)", "highlight": "#f59e0b"},
                "confidence": e.confidence.value if hasattr(e.confidence, "value") else str(e.confidence),
            })

    nodes_json = json.dumps(vis_nodes)
    edges_json = json.dumps(vis_edges)

    # Community legend items
    comm_items_html = []
    for cid, name in sorted(community_labels.items()):
        cnt = len(communities.get(cid, []))
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        comm_items_html.append(
            f'<div class="legend-item" data-cid="{cid}">'
            f'<input type="checkbox" class="legend-cb" data-cid="{cid}" checked />'
            f'<span class="legend-dot" style="background:{color};"></span>'
            f'<span class="legend-name" title="{name}">{name}</span>'
            f'<span class="legend-count">({cnt})</span>'
            f'</div>'
        )
    comm_legend_block = "\n".join(comm_items_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>RepoPeek Knowledge Graph</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; height: 100vh; overflow: hidden; }}
    #graph-container {{ flex: 1; height: 100%; position: relative; }}
    #sidebar {{ width: 320px; background: #111827; border-left: 1px solid #1f2937; display: flex; flex-direction: column; overflow: hidden; z-index: 10; }}
    #search-box {{ padding: 12px; border-bottom: 1px solid #1f2937; }}
    #search-input {{ width: 100%; padding: 8px 12px; background: #1f2937; border: 1px solid #374151; border-radius: 6px; color: #fff; font-size: 13px; outline: none; }}
    #search-input:focus {{ border-color: #3b82f6; }}
    #inspector {{ padding: 14px; border-bottom: 1px solid #1f2937; min-height: 160px; max-height: 260px; overflow-y: auto; }}
    #inspector h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; margin-bottom: 8px; }}
    .field {{ margin-bottom: 6px; font-size: 13px; word-break: break-all; }}
    .field b {{ color: #93c5fd; }}
    #legend-container {{ flex: 1; padding: 12px; overflow-y: auto; }}
    #legend-container h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; margin-bottom: 10px; }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; padding: 4px 6px; border-radius: 4px; font-size: 12px; cursor: pointer; }}
    .legend-item:hover {{ background: #1f2937; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
    .legend-name {{ flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .legend-count {{ color: #6b7280; font-size: 11px; }}
    #stats-bar {{ padding: 10px 14px; border-top: 1px solid #1f2937; font-size: 11px; color: #6b7280; }}
  </style>
</head>
<body>
  <div id="graph-container"></div>
  <div id="sidebar">
    <div id="search-box">
      <input type="text" id="search-input" placeholder="Search symbols, files, classes..." />
    </div>
    <div id="inspector">
      <h3>Node Inspector</h3>
      <div id="inspect-content" style="color:#9ca3af; font-size:12px; font-style:italic;">Click any node to inspect details, file boundaries, and connections.</div>
    </div>
    <div id="legend-container">
      <h3>Modular Communities</h3>
      {comm_legend_block}
    </div>
    <div id="stats-bar">
      Total Rendered: {len(vis_nodes)} nodes | {len(vis_edges)} edges
    </div>
  </div>

  <script type="text/javascript">
    const rawNodes = {nodes_json};
    const rawEdges = {edges_json};

    const container = document.getElementById('graph-container');
    const nodes = new vis.DataSet(rawNodes);
    const edges = new vis.DataSet(rawEdges);

    const data = {{ nodes: nodes, edges: edges }};
    const options = {{
      nodes: {{
        shape: 'dot',
        font: {{ face: 'sans-serif', size: 12, color: '#e2e8f0' }},
        scaling: {{ min: 10, max: 40 }}
      }},
      edges: {{
        width: 1,
        smooth: {{ type: 'continuous' }},
        font: {{ size: 9, color: '#94a3b8', strokeWidth: 0 }}
      }},
      physics: {{
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {{
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 80,
          springConstant: 0.08
        }},
        maxVelocity: 50,
        minVelocity: 0.1,
        stabilization: {{ iterations: 100 }}
      }},
      interaction: {{ hover: true, tooltipDelay: 100 }}
    }};

    const network = new vis.Network(container, data, options);

    // Inspector
    network.on('click', function(params) {{
      if (params.nodes.length > 0) {{
        const nid = params.nodes[0];
        const n = nodes.get(nid);
        if (n) {{
          document.getElementById('inspect-content').innerHTML = `
            <div class="field"><b>Symbol:</b> ${{n.label}}</div>
            <div class="field"><b>Kind:</b> ${{n.kind}}</div>
            <div class="field"><b>Community:</b> ${{n.community_name}}</div>
            <div class="field"><b>Degree:</b> ${{n.degree}} connections</div>
            <div class="field"><b>File:</b> ${{n.file || 'internal'}}</div>
            <div class="field"><b>ID:</b> <code style="font-size:10px; color:#cbd5e1;">${{n.id}}</code></div>
          `;
        }}
      }}
    }});

    // Search
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', function(e) {{
      const term = e.target.value.toLowerCase().trim();
      if (!term) return;
      const matched = nodes.get({{
        filter: function(item) {{
          return item.label.toLowerCase().includes(term) || (item.file && item.file.toLowerCase().includes(term));
        }}
      }});
      if (matched.length > 0) {{
        network.focus(matched[0].id, {{ scale: 1.2, animation: true }});
      }}
    }});

    // Community visibility toggles
    document.querySelectorAll('.legend-cb').forEach(cb => {{
      cb.addEventListener('change', function(e) {{
        const cid = parseInt(e.target.dataset.cid);
        const visible = e.target.checked;
        const targetNodes = nodes.get({{ filter: n => n.community === cid }});
        targetNodes.forEach(n => {{
          nodes.update({{ id: n.id, hidden: !visible }});
        }});
      }});
    }});
  </script>
</body>
</html>
"""

    out_path.write_text(html_content, encoding="utf-8")
    return out_path
