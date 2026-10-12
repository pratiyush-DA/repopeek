"""High-Performance Obsidian-Style Graph Visualization Engine for RepoPeek.

Dual-layer architecture:
- Layer 1: HTML5 Canvas 2D renderer supporting >5,000 nodes & >15,000 edges at 60 FPS.
- Layer 2: Glassmorphic HTML/CSS overlay for navigation, search, inspector, and physics controls.
"""

from __future__ import annotations

import json
import math
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


def generate_html_content(
    graph: CanonicalGraph,
    communities: Optional[Dict[int, List[str]]] = None,
    community_labels: Optional[Dict[int, str]] = None,
    max_nodes: int = 6000,
) -> str:
    """Generate self-contained Obsidian-style interactive graph HTML string."""

    if communities is None:
        communities = detect_communities(graph)
    if community_labels is None:
        community_labels = generate_community_labels(graph, communities)

    node_to_comm: Dict[str, int] = {}
    for cid, members in communities.items():
        for mid in members:
            node_to_comm[mid] = cid

    # 1. Degree Centrality (in, out, total)
    in_degrees: Dict[str, int] = {nid: 0 for nid in graph.nodes}
    out_degrees: Dict[str, int] = {nid: 0 for nid in graph.nodes}
    for e in graph.edges:
        out_degrees[e.src] = out_degrees.get(e.src, 0) + 1
        in_degrees[e.dst] = in_degrees.get(e.dst, 0) + 1

    degrees: Dict[str, int] = {
        nid: in_degrees.get(nid, 0) + out_degrees.get(nid, 0)
        for nid in graph.nodes
    }

    # 2. Sort nodes by degree and cap if exceeding max_nodes
    sorted_node_ids = sorted(graph.nodes.keys(), key=lambda nid: degrees.get(nid, 0), reverse=True)
    if len(sorted_node_ids) > max_nodes:
        sorted_node_ids = sorted_node_ids[:max_nodes]
    included_set = set(sorted_node_ids)

    # 3. Fast Adjacency Map for 1-hop & reachable blast radius
    adj: Dict[str, List[str]] = {nid: [] for nid in included_set}
    inc_edges: Dict[str, List[int]] = {nid: [] for nid in included_set}

    canvas_edges: List[Dict[str, Any]] = []
    edge_idx = 0
    for e in graph.edges:
        if e.src in included_set and e.dst in included_set:
            edge_type = e.type.value if hasattr(e.type, "value") else str(e.type)
            conf = e.confidence.value if hasattr(e.confidence, "value") else str(e.confidence)
            canvas_edges.append({
                "source": e.src,
                "target": e.dst,
                "type": edge_type,
                "confidence": conf,
            })
            adj[e.src].append(e.dst)
            adj[e.dst].append(e.src)
            inc_edges[e.src].append(edge_idx)
            inc_edges[e.dst].append(edge_idx)
            edge_idx += 1

    # Deduplicate adjacency lists
    for nid in adj:
        adj[nid] = list(set(adj[nid]))

    # 4. Serialize Nodes with Dynamic Relevance Sizing
    # Radius formula: clamp(3.5, 3.5 + 3.2 * log(1 + degree), 22.0)
    canvas_nodes: List[Dict[str, Any]] = []
    for nid in sorted_node_ids:
        card = graph.nodes[nid]
        deg = degrees.get(nid, 0)
        in_deg = in_degrees.get(nid, 0)
        out_deg = out_degrees.get(nid, 0)

        raw_radius = 3.5 + 3.2 * math.log(1.0 + deg)
        radius = max(3.5, min(22.0, raw_radius))

        cid = node_to_comm.get(nid, 0)
        cname = community_labels.get(cid, f"Community {cid}")
        comm_color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]

        is_external = card.kind == "external_symbol" or nid.startswith("ext:")
        resting_color = "#6e7681" if is_external else "#c9d1d9"

        # Crisp Obsidian-style label: clean identifier name rather than long multi-line signatures
        raw_name = nid.split("::")[-1]
        if not raw_name or raw_name == nid or raw_name.startswith("py:"):
            if card.span and card.span.file:
                raw_name = Path(card.span.file).name
            else:
                raw_name = nid.split("/")[-1]
        if raw_name.startswith("def "):
            raw_name = raw_name[4:].strip()
        elif raw_name.startswith("class "):
            raw_name = raw_name[6:].strip()
        if "(" in raw_name:
            raw_name = raw_name.split("(")[0].strip()
        if len(raw_name) > 28:
            raw_name = raw_name[:26] + ".."
        label = raw_name or nid
        full_sig = card.sig or label

        file_path = card.span.file if card.span else ""

        # Precompute reachable blast radius count (BFS 2 hops)
        reachable = set([nid])
        frontier = set([nid])
        for _ in range(2):
            next_frontier = set()
            for cur in frontier:
                for nbr in adj.get(cur, []):
                    if nbr not in reachable:
                        reachable.add(nbr)
                        next_frontier.add(nbr)
            frontier = next_frontier

        canvas_nodes.append({
            "id": nid,
            "label": label,
            "signature": full_sig,
            "kind": card.kind,
            "file": file_path,
            "radius": round(radius, 2),
            "degree": deg,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "community": cid,
            "community_name": cname,
            "comm_color": comm_color,
            "resting_color": resting_color,
            "is_external": is_external,
            "blast_radius_count": len(reachable) - 1,
            "neighbors": adj.get(nid, []),
            "incident_edges": inc_edges.get(nid, []),
        })

    nodes_json = json.dumps(canvas_nodes)
    edges_json = json.dumps(canvas_edges)
    communities_json = json.dumps(community_labels)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RepoPeek Knowledge Graph</title>
  <!-- D3.js v7 CDN -->
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
    }}

    body, html {{
      width: 100%;
      height: 100%;
      overflow: hidden;
      background-color: #161618;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "IBM Plex Sans", Roboto, Helvetica, Arial, sans-serif;
    }}

    /* Layer 1: Canvas */
    #canvas-viewport {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      display: block;
      cursor: grab;
      z-index: 1;
    }}
    #canvas-viewport:active {{
      cursor: grabbing;
    }}

    /* Layer 2: Glassmorphic UI Overlays */
    .glass-panel {{
      background: rgba(22, 22, 24, 0.78);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
      z-index: 10;
    }}

    /* Top Navigation Bar */
    #nav-header {{
      position: absolute;
      top: 14px;
      left: 14px;
      right: 14px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      z-index: 20;
    }}

    .nav-left {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      font-weight: 500;
      color: #8b949e;
    }}

    .nav-breadcrumb {{
      display: flex;
      align-items: center;
      gap: 6px;
      color: #e6edf3;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}

    .nav-arrows {{
      color: #484f58;
      font-weight: 400;
      font-size: 14px;
    }}

    .nav-center {{
      flex: 1;
      max-width: 440px;
      margin: 0 20px;
      position: relative;
    }}

    #search-input {{
      width: 100%;
      height: 32px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      padding: 0 32px 0 12px;
      color: #f0f6fc;
      font-size: 12.5px;
      outline: none;
      transition: all 0.15s ease;
    }}
    #search-input:focus {{
      border-color: #58a6ff;
      background: rgba(255, 255, 255, 0.1);
    }}
    #search-input::placeholder {{
      color: #6e7681;
    }}

    #search-count {{
      position: absolute;
      right: 10px;
      top: 8px;
      font-size: 11px;
      color: #8b949e;
      pointer-events: none;
    }}

    .nav-right {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .icon-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      color: #c9d1d9;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.15s ease;
    }}
    .icon-btn:hover {{
      background: rgba(255, 255, 255, 0.12);
      color: #ffffff;
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .icon-btn.active {{
      background: rgba(224, 85, 97, 0.2);
      border-color: #e05561;
      color: #e05561;
    }}

    /* Controls Drawer */
    #controls-drawer {{
      position: absolute;
      top: 72px;
      right: 14px;
      width: 290px;
      padding: 16px;
      display: none;
      flex-direction: column;
      gap: 14px;
      z-index: 25;
    }}
    #controls-drawer.open {{
      display: flex;
    }}

    .drawer-title {{
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #8b949e;
      margin-bottom: 2px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .control-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .control-label {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #c9d1d9;
    }}

    .control-val {{
      color: #8b949e;
      font-family: monospace;
      font-size: 11px;
    }}

    input[type=range] {{
      -webkit-appearance: none;
      width: 100%;
      height: 4px;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 2px;
      outline: none;
    }}
    input[type=range]::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #c9d1d9;
      cursor: pointer;
      transition: background 0.15s;
    }}
    input[type=range]::-webkit-slider-thumb:hover {{
      background: #e05561;
    }}

    .toggle-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: #c9d1d9;
      padding-top: 4px;
    }}

    /* Instant Hover Micro-Card */
    #hover-card {{
      position: absolute;
      pointer-events: none;
      display: none;
      padding: 10px 14px;
      max-width: 320px;
      font-size: 12px;
      line-height: 1.4;
      z-index: 30;
      border: 1px solid rgba(224, 85, 97, 0.4);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }}

    .hover-name {{
      font-weight: 600;
      font-size: 13px;
      color: #f0f6fc;
      margin-bottom: 3px;
      word-break: break-all;
    }}

    .hover-badge {{
      display: inline-block;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      padding: 1px 6px;
      border-radius: 3px;
      margin-bottom: 6px;
    }}

    .hover-meta {{
      color: #8b949e;
      font-size: 11px;
    }}
    .hover-meta b {{
      color: #c9d1d9;
    }}

    /* Pinned Selection Inspector Drawer */
    #inspector-drawer {{
      position: absolute;
      bottom: 14px;
      right: 14px;
      width: 360px;
      max-height: 380px;
      display: none;
      flex-direction: column;
      padding: 16px;
      z-index: 20;
      overflow-y: auto;
    }}
    #inspector-drawer.open {{
      display: flex;
    }}

    .insp-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }}

    .insp-title {{
      font-size: 14px;
      font-weight: 600;
      color: #f0f6fc;
      word-break: break-all;
    }}

    .insp-close {{
      background: none;
      border: none;
      color: #8b949e;
      cursor: pointer;
      font-size: 16px;
      padding: 0 4px;
    }}
    .insp-close:hover {{
      color: #ffffff;
    }}

    .insp-section {{
      margin-top: 10px;
      font-size: 11.5px;
    }}
    .insp-sec-title {{
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #8b949e;
      margin-bottom: 4px;
    }}

    .insp-list {{
      max-height: 90px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}
    .insp-item {{
      background: rgba(255, 255, 255, 0.03);
      padding: 3px 6px;
      border-radius: 3px;
      color: #c9d1d9;
      font-size: 11px;
      font-family: monospace;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    /* Bottom Stats Bar */
    #status-bar {{
      position: absolute;
      bottom: 14px;
      left: 14px;
      padding: 6px 12px;
      font-size: 11.5px;
      color: #8b949e;
      display: flex;
      gap: 12px;
      z-index: 10;
    }}
    #status-bar span b {{
      color: #c9d1d9;
    }}
  </style>
</head>
<body>
  <!-- Layer 1: High-Performance Canvas 2D Viewport -->
  <canvas id="canvas-viewport" class="graph-canvas"></canvas>

  <!-- Layer 2: Glassmorphic Overlay Chrome -->
  <header id="nav-header" class="glass-panel">
    <div class="nav-left">
      <span class="nav-arrows">&larr; &rarr;</span>
      <span class="nav-breadcrumb">Graph view</span>
    </div>

    <div class="nav-center">
      <input type="text" id="search-input" placeholder="Search files, symbols, classes..." autocomplete="off" />
      <span id="search-count"></span>
    </div>

    <div class="nav-right">
      <button id="btn-color-mode" class="icon-btn" title="Toggle Community / Monochromatic Color Mode">&#9681;</button>
      <button id="btn-reset-view" class="icon-btn" title="Reset View & Center">&#8982;</button>
      <button id="btn-settings" class="icon-btn" title="Physics & Force Settings">&#9881;</button>
    </div>
  </header>

  <!-- Collapsible Controls Drawer -->
  <aside id="controls-drawer" class="glass-panel">
    <div class="drawer-title">
      <span>Physics & Forces</span>
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>Center Force</span>
        <span id="val-center" class="control-val">0.015</span>
      </div>
      <input type="range" id="slider-center" min="0.001" max="0.08" step="0.001" value="0.015" />
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>Repel / Charge</span>
        <span id="val-charge" class="control-val">-140</span>
      </div>
      <input type="range" id="slider-charge" min="-400" max="-30" step="10" value="-140" />
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>Link Distance</span>
        <span id="val-distance" class="control-val">55</span>
      </div>
      <input type="range" id="slider-distance" min="20" max="150" step="5" value="55" />
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>Collision Padding</span>
        <span id="val-collide" class="control-val">4</span>
      </div>
      <input type="range" id="slider-collide" min="0" max="15" step="1" value="4" />
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>Edge Resting Opacity</span>
        <span id="val-edge-op" class="control-val">0.22</span>
      </div>
      <input type="range" id="slider-edge-op" min="0.05" max="0.80" step="0.01" value="0.22" />
    </div>

    <div class="toggle-row">
      <span>Semantic Text LOD</span>
      <input type="checkbox" id="chk-lod" checked />
    </div>
  </aside>

  <!-- Instant Hover Micro-Card -->
  <div id="hover-card" class="glass-panel">
    <div id="hover-name" class="hover-name"></div>
    <div id="hover-badge" class="hover-badge"></div>
    <div class="hover-meta">
      <div>File: <b id="hover-file"></b></div>
      <div>Degree: <b id="hover-degree"></b> (<b id="hover-in"></b> in &middot; <b id="hover-out"></b> out)</div>
      <div>Blast Radius (2-hop): <b id="hover-blast" style="color:#e05561;"></b> reachable nodes</div>
    </div>
  </div>

  <!-- Pinned Selection Inspector Drawer -->
  <aside id="inspector-drawer" class="glass-panel">
    <div class="insp-header">
      <div>
        <div id="insp-name" class="insp-title"></div>
        <div id="insp-badge" class="hover-badge" style="margin-top:4px;"></div>
      </div>
      <button id="insp-close-btn" class="insp-close">&times;</button>
    </div>

    <div class="insp-section">
      <div>File: <b id="insp-file" style="color:#f0f6fc; word-break:break-all;"></b></div>
      <div>Degree: <b id="insp-degree" style="color:#f0f6fc;"></b> connections</div>
      <div>Reachable Blast Radius: <b id="insp-blast" style="color:#e05561;"></b> nodes</div>
    </div>

    <div class="insp-section">
      <div class="insp-sec-title">Connected Neighbors (<span id="insp-nbr-count"></span>)</div>
      <div id="insp-nbr-list" class="insp-list"></div>
    </div>
  </aside>

  <!-- Bottom Status Bar -->
  <footer id="status-bar" class="glass-panel">
    <span>Rendered: <b id="stat-nodes">{len(canvas_nodes)}</b> nodes</span>
    <span>&middot;</span>
    <span>Links: <b id="stat-edges">{len(canvas_edges)}</b> edges</span>
    <span>&middot;</span>
    <span>Zoom: <b id="stat-zoom">1.00x</b></span>
    <span>&middot;</span>
    <span>FPS: <b id="stat-fps">60</b></span>
  </footer>

  <script>
    // Embedded Data Payload
    const rawNodes = {nodes_json};
    const rawEdges = {edges_json};
    const communityMap = {communities_json};

    // Node & Edge Index Maps for O(1) Lookups
    const nodeById = new Map();
    rawNodes.forEach(n => {{
      n.degree = n.degree || 0;
      nodeById.set(n.id, n);
    }});

    // Prepare Link References for D3 Force
    const links = rawEdges.map(e => ({{
      source: e.source,
      target: e.target,
      type: e.type,
      confidence: e.confidence,
    }}));

    // Canvas & HiDPI Context Setup
    const canvas = document.getElementById('canvas-viewport');
    const ctx = canvas.getContext('2d', {{ alpha: false }});
    let width = window.innerWidth;
    let height = window.innerHeight;
    let dpr = window.devicePixelRatio || 1;

    function resizeCanvas() {{
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      ctx.scale(dpr, dpr);
    }}
    resizeCanvas();
    window.addEventListener('resize', () => {{
      resizeCanvas();
      if (simulation) {{
        simulation.force('center', d3.forceCenter(width / 2, height / 2));
      }}
      requestRender();
    }});

    // D3 Force Simulation Setup
    let forceCharge = -140;
    let forceDistance = 55;
    let forceCenterStrength = 0.015;
    let forceCollidePadding = 4;
    let edgeRestingOpacity = 0.22;
    let useCommunityColors = false;
    let enableSemanticLOD = true;

    // Disperse nodes by modular community in a ring to avoid center explosion
    const commAngles = {{}};
    const commKeys = Object.keys(communityMap || {{}});
    const commTotal = Math.max(1, commKeys.length);
    const ringRadius = Math.min(width, height) * 0.35;
    for (let i = 0; i < rawNodes.length; i++) {{
      const n = rawNodes[i];
      const cid = n.community || 0;
      if (!(cid in commAngles)) {{
        commAngles[cid] = (cid / commTotal) * 2 * Math.PI;
      }}
      const angle = commAngles[cid] + (Math.random() - 0.5) * 0.7;
      const dist = ringRadius + (Math.random() - 0.5) * (ringRadius * 0.6);
      n.x = (width / 2) + Math.cos(angle) * dist;
      n.y = (height / 2) + Math.sin(angle) * dist;
    }}

    const simulation = d3.forceSimulation(rawNodes)
      .force('link', d3.forceLink(links)
        .id(d => d.id)
        .distance(forceDistance)
        .strength(d => 1 / Math.min(d.source.degree || 1, d.target.degree || 1, 15))
      )
      .force('charge', d3.forceManyBody()
        .strength(forceCharge)
        .theta(0.92)
        .distanceMax(450)
      )
      .force('collide', d3.forceCollide()
        .radius(d => d.radius + forceCollidePadding)
        .iterations(1)
      )
      .force('center', d3.forceCenter(width / 2, height / 2).strength(forceCenterStrength))
      .alphaDecay(0.025);

    // Initial Warmup
    for (let i = 0; i < 40; ++i) simulation.tick();

    // Zoom & Pan State
    let transform = d3.zoomIdentity;
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.05, 12])
      .on('zoom', (event) => {{
        transform = event.transform;
        document.getElementById('stat-zoom').textContent = transform.k.toFixed(2) + 'x';
        requestRender();
      }});

    d3.select(canvas)
      .call(zoomBehavior)
      .on('dblclick.zoom', null);

    // Selection & Spotlight State
    let hoveredNode = null;
    let pinnedNode = null;
    let hoverTransitionAlpha = 0.0;
    let lastRenderTime = performance.now();
    let frameCount = 0;
    let fpsTime = performance.now();

    // Render Loop with Dirty Flag
    let renderRequested = false;
    function requestRender() {{
      if (!renderRequested) {{
        renderRequested = true;
        requestAnimationFrame(renderFrame);
      }}
    }}

    simulation.on('tick', () => {{
      requestRender();
    }});

    // Color Constants (Obsidian Palette)
    const COLOR_BG = '#161618';
    const COLOR_NODE_REST = '#c9d1d9';
    const COLOR_NODE_EXT = '#6e7681';
    const COLOR_EDGE_REST = '#2f3542';
    const COLOR_SPOTLIGHT = '#e05561';

    function renderFrame(now) {{
      renderRequested = false;

      // Calculate FPS
      frameCount++;
      if (now - fpsTime >= 500) {{
        const fps = Math.round((frameCount * 1000) / (now - fpsTime));
        document.getElementById('stat-fps').textContent = fps;
        frameCount = 0;
        fpsTime = now;
      }}

      // Interpolate hover spotlight transition alpha
      const targetAlpha = (hoveredNode || pinnedNode) ? 1.0 : 0.0;
      if (Math.abs(hoverTransitionAlpha - targetAlpha) > 0.01) {{
        const dt = Math.min(32, now - lastRenderTime);
        hoverTransitionAlpha += (targetAlpha - hoverTransitionAlpha) * (dt / 200);
        requestRender();
      }} else {{
        hoverTransitionAlpha = targetAlpha;
      }}
      lastRenderTime = now;

      const k = transform.k;
      const tx = transform.x;
      const ty = transform.y;

      // Clear Canvas
      ctx.save();
      ctx.fillStyle = COLOR_BG;
      ctx.fillRect(0, 0, width, height);

      // Apply World Transform
      ctx.translate(tx, ty);
      ctx.scale(k, k);

      const activeNode = pinnedNode || hoveredNode;
      let activeNeighborSet = null;
      let activeIncidentEdgeSet = null;

      if (activeNode) {{
        activeNeighborSet = new Set(activeNode.neighbors);
        activeNeighborSet.add(activeNode.id);
        activeIncidentEdgeSet = new Set(activeNode.incident_edges);
      }}

      // 1. Render Edges
      for (let i = 0; i < links.length; i++) {{
        const l = links[i];
        const sx = l.source.x;
        const sy = l.source.y;
        const tx_ = l.target.x;
        const ty_ = l.target.y;

        // Viewport frustum culling in screen space
        const scrMinX = (Math.min(sx, tx_) * k) + tx;
        const scrMaxX = (Math.max(sx, tx_) * k) + tx;
        const scrMinY = (Math.min(sy, ty_) * k) + ty;
        const scrMaxY = (Math.max(sy, ty_) * k) + ty;
        if (scrMaxX < 0 || scrMinX > width || scrMaxY < 0 || scrMinY > height) {{
          continue;
        }}

        const isIncident = activeIncidentEdgeSet && activeIncidentEdgeSet.has(i);

        if (isIncident) {{
          // Highlighted incident edge
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(tx_, ty_);
          ctx.strokeStyle = COLOR_SPOTLIGHT;
          ctx.lineWidth = 2.0 / k;
          ctx.globalAlpha = 0.95;
          ctx.stroke();
        }} else {{
          // Resting or dimmed edge
          const baseAlpha = edgeRestingOpacity;
          const dimmedAlpha = 0.02;
          const alpha = (activeNode && hoverTransitionAlpha > 0)
            ? (baseAlpha * (1.0 - hoverTransitionAlpha) + dimmedAlpha * hoverTransitionAlpha)
            : baseAlpha;

          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(tx_, ty_);
          ctx.strokeStyle = COLOR_EDGE_REST;
          ctx.lineWidth = 0.8 / k;
          ctx.globalAlpha = alpha;
          ctx.stroke();
        }}
      }}

      // 2. Render Nodes
      ctx.globalAlpha = 1.0;
      for (let i = 0; i < rawNodes.length; i++) {{
        const n = rawNodes[i];
        const nx = n.x;
        const ny = n.y;
        const r = n.radius;

        // Frustum Culling
        const scrX = (nx * k) + tx;
        const scrY = (ny * k) + ty;
        const scrR = r * k;
        if (scrX + scrR < 0 || scrX - scrR > width || scrY + scrR < 0 || scrY - scrR > height) {{
          continue;
        }}

        const isActive = activeNode && (activeNode.id === n.id);
        const isNeighbor = activeNeighborSet && activeNeighborSet.has(n.id);

        let nodeColor = useCommunityColors ? n.comm_color : n.resting_color;
        let nodeAlpha = 1.0;

        if (activeNode) {{
          if (isActive) {{
            nodeColor = COLOR_SPOTLIGHT;
            nodeAlpha = 1.0;

            // Radial Glow Halo for active node
            const glowR = r * 2.8;
            const gradient = ctx.createRadialGradient(nx, ny, r * 0.8, nx, ny, glowR);
            gradient.addColorStop(0, 'rgba(224, 85, 97, 0.45)');
            gradient.addColorStop(1, 'rgba(224, 85, 97, 0.0)');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(nx, ny, glowR, 0, Math.PI * 2);
            ctx.fill();
          }} else if (isNeighbor) {{
            nodeAlpha = 1.0;
          }} else {{
            nodeAlpha = 1.0 * (1.0 - hoverTransitionAlpha) + 0.08 * hoverTransitionAlpha;
          }}
        }}

        // Draw Node Glyph
        ctx.beginPath();
        ctx.arc(nx, ny, r, 0, Math.PI * 2);
        ctx.fillStyle = nodeColor;
        ctx.globalAlpha = nodeAlpha;
        ctx.fill();

        // White/silver boundary emphasis on neighbors & active
        if (isActive || (isNeighbor && hoverTransitionAlpha > 0.3)) {{
          ctx.strokeStyle = isActive ? '#ffffff' : 'rgba(255, 255, 255, 0.65)';
          ctx.lineWidth = (isActive ? 1.8 : 1.0) / k;
          ctx.stroke();
        }}
      }}

      // 3. Render Text Labels with Optical Screen-Space Clamping & Semantic LOD
      // Clamping math: clamp(10, 10 / (k ** 0.15), 13) px
      const screenFontSize = Math.min(13, Math.max(10, 10 / Math.pow(k, 0.15)));
      const worldFontSize = screenFontSize / k;
      ctx.font = `${{worldFontSize}}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      for (let i = 0; i < rawNodes.length; i++) {{
        const n = rawNodes[i];
        const nx = n.x;
        const ny = n.y;
        const deg = n.degree;

        // Frustum culling
        const scrX = (nx * k) + tx;
        const scrY = (ny * k) + ty;
        if (scrX < -80 || scrX > width + 80 || scrY < -80 || scrY > height + 80) {{
          continue;
        }}

        const isActive = activeNode && (activeNode.id === n.id);
        const isNeighbor = activeNeighborSet && activeNeighborSet.has(n.id);

        // LOD Visibility Gate
        let showLabel = false;
        if (isActive || isNeighbor) {{
          showLabel = true;
        }} else if (!enableSemanticLOD) {{
          showLabel = true;
        }} else if (k < 0.6) {{
          showLabel = (deg > 20);
        }} else if (k < 1.4) {{
          showLabel = (deg > 8) || (n.kind === 'class') || (n.kind === 'file');
        }} else if (k < 2.8) {{
          showLabel = (deg > 2) || (n.kind === 'class') || (n.kind === 'file');
        }} else {{
          showLabel = true;
        }}

        if (!showLabel) continue;

        let labelAlpha = 0.85;
        let labelColor = '#c9d1d9';

        if (activeNode) {{
          if (isActive) {{
            labelAlpha = 1.0;
            labelColor = '#ffffff';
          }} else if (isNeighbor) {{
            labelAlpha = 0.95;
            labelColor = '#f0f6fc';
          }} else {{
            labelAlpha = 0.85 * (1.0 - hoverTransitionAlpha) + 0.05 * hoverTransitionAlpha;
          }}
        }}

        ctx.fillStyle = labelColor;
        ctx.globalAlpha = labelAlpha;

        // Subtle text shadow for high contrast
        ctx.fillText(n.label, nx, ny + n.radius + (3.0 / k));
      }}

      ctx.restore();
    }}

    // Spatial Hit Test for Pointer Events
    function findNodeAtScreen(screenX, screenY) {{
      const worldX = (screenX - transform.x) / transform.k;
      const worldY = (screenY - transform.y) / transform.k;

      // Generous hit radius in screen pixels (minimum 12px)
      const minHitR = 12 / transform.k;

      let closest = null;
      let minDistanceSq = Infinity;

      for (let i = 0; i < rawNodes.length; i++) {{
        const n = rawNodes[i];
        const dx = worldX - n.x;
        const dy = worldY - n.y;
        const distSq = dx * dx + dy * dy;
        const hitR = Math.max(n.radius, minHitR);

        if (distSq <= hitR * hitR) {{
          if (distSq < minDistanceSq) {{
            minDistanceSq = distSq;
            closest = n;
          }}
        }}
      }}
      return closest;
    }}

    // Hover Spotlight & Micro-Card Interaction
    const hoverCard = document.getElementById('hover-card');
    const hoverName = document.getElementById('hover-name');
    const hoverBadge = document.getElementById('hover-badge');
    const hoverFile = document.getElementById('hover-file');
    const hoverDegree = document.getElementById('hover-degree');
    const hoverIn = document.getElementById('hover-in');
    const hoverOut = document.getElementById('hover-out');
    const hoverBlast = document.getElementById('hover-blast');

    canvas.addEventListener('mousemove', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const hit = findNodeAtScreen(mouseX, mouseY);

      if (hit !== hoveredNode) {{
        hoveredNode = hit;
        requestRender();

        if (hoveredNode && !pinnedNode) {{
          hoverName.textContent = hoveredNode.signature || hoveredNode.label;
          hoverBadge.textContent = hoveredNode.kind || 'symbol';
          hoverBadge.style.background = hoveredNode.comm_color + '33';
          hoverBadge.style.color = hoveredNode.comm_color;
          hoverFile.textContent = hoveredNode.file || 'internal';
          hoverDegree.textContent = hoveredNode.degree;
          hoverIn.textContent = hoveredNode.in_degree;
          hoverOut.textContent = hoveredNode.out_degree;
          hoverBlast.textContent = hoveredNode.blast_radius_count;

          hoverCard.style.display = 'block';
        }} else if (!pinnedNode) {{
          hoverCard.style.display = 'none';
        }}
      }}

      if (hoverCard.style.display === 'block') {{
        // Offset microcard from cursor
        const cardX = Math.min(window.innerWidth - 340, mouseX + 16);
        const cardY = Math.min(window.innerHeight - 150, mouseY + 16);
        hoverCard.style.left = cardX + 'px';
        hoverCard.style.top = cardY + 'px';
      }}
    }});

    canvas.addEventListener('mouseleave', () => {{
      hoveredNode = null;
      hoverCard.style.display = 'none';
      requestRender();
    }});

    // Click to Pin / Detailed Inspector
    const inspDrawer = document.getElementById('inspector-drawer');
    const inspName = document.getElementById('insp-name');
    const inspBadge = document.getElementById('insp-badge');
    const inspFile = document.getElementById('insp-file');
    const inspDegree = document.getElementById('insp-degree');
    const inspBlast = document.getElementById('insp-blast');
    const inspNbrCount = document.getElementById('insp-nbr-count');
    const inspNbrList = document.getElementById('insp-nbr-list');
    const inspCloseBtn = document.getElementById('insp-close-btn');

    function pinNode(node) {{
      pinnedNode = node;
      hoverCard.style.display = 'none';

      if (pinnedNode) {{
        inspName.textContent = pinnedNode.signature || pinnedNode.label;
        inspBadge.textContent = pinnedNode.kind || 'symbol';
        inspBadge.style.background = pinnedNode.comm_color + '33';
        inspBadge.style.color = pinnedNode.comm_color;
        inspFile.textContent = pinnedNode.file || 'internal';
        inspDegree.textContent = pinnedNode.degree;
        inspBlast.textContent = pinnedNode.blast_radius_count;
        inspNbrCount.textContent = pinnedNode.neighbors.length;

        inspNbrList.innerHTML = '';
        pinnedNode.neighbors.forEach(nid => {{
          const nbr = nodeById.get(nid);
          const div = document.createElement('div');
          div.className = 'insp-item';
          div.textContent = nbr ? nbr.label : nid;
          div.style.cursor = 'pointer';
          div.addEventListener('click', (ev) => {{
            ev.stopPropagation();
            if (nbr) focusNode(nbr);
          }});
          inspNbrList.appendChild(div);
        }});

        inspDrawer.classList.add('open');
      }} else {{
        inspDrawer.classList.remove('open');
      }}
      requestRender();
    }}

    canvas.addEventListener('click', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const hit = findNodeAtScreen(mouseX, mouseY);
      pinNode(hit);
    }});

    inspCloseBtn.addEventListener('click', () => {{
      pinNode(null);
    }});

    function focusNode(node) {{
      pinNode(node);
      const targetScale = Math.max(transform.k, 1.8);
      const targetX = width / 2 - node.x * targetScale;
      const targetY = height / 2 - node.y * targetScale;

      d3.select(canvas)
        .transition()
        .duration(600)
        .call(
          zoomBehavior.transform,
          d3.zoomIdentity.translate(targetX, targetY).scale(targetScale)
        );
    }}

    // Fuzzy Search Navigation
    const searchInput = document.getElementById('search-input');
    const searchCount = document.getElementById('search-count');

    searchInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase().trim();
      if (!q) {{
        searchCount.textContent = '';
        pinNode(null);
        return;
      }}

      const matches = rawNodes.filter(n =>
        n.label.toLowerCase().includes(q) ||
        (n.file && n.file.toLowerCase().includes(q))
      );

      searchCount.textContent = `${{matches.length}} matches`;

      if (matches.length > 0) {{
        focusNode(matches[0]);
      }}
    }});

    // Reset View Button
    document.getElementById('btn-reset-view').addEventListener('click', () => {{
      d3.select(canvas)
        .transition()
        .duration(500)
        .call(zoomBehavior.transform, d3.zoomIdentity);
      pinNode(null);
    }});

    // Color Mode Toggle Button
    const btnColorMode = document.getElementById('btn-color-mode');
    btnColorMode.addEventListener('click', () => {{
      useCommunityColors = !useCommunityColors;
      btnColorMode.classList.toggle('active', useCommunityColors);
      requestRender();
    }});

    // Settings Drawer Toggle
    const btnSettings = document.getElementById('btn-settings');
    const controlsDrawer = document.getElementById('controls-drawer');
    btnSettings.addEventListener('click', () => {{
      controlsDrawer.classList.toggle('open');
      btnSettings.classList.toggle('active');
    }});

    // Physics Controls Handlers
    const sliderCenter = document.getElementById('slider-center');
    const valCenter = document.getElementById('val-center');
    sliderCenter.addEventListener('input', (e) => {{
      const v = parseFloat(e.target.value);
      valCenter.textContent = v.toFixed(3);
      simulation.force('center').strength(v);
      simulation.alpha(0.2).restart();
    }});

    const sliderCharge = document.getElementById('slider-charge');
    const valCharge = document.getElementById('val-charge');
    sliderCharge.addEventListener('input', (e) => {{
      const v = parseFloat(e.target.value);
      valCharge.textContent = v;
      simulation.force('charge').strength(v);
      simulation.alpha(0.25).restart();
    }});

    const sliderDistance = document.getElementById('slider-distance');
    const valDistance = document.getElementById('val-distance');
    sliderDistance.addEventListener('input', (e) => {{
      const v = parseFloat(e.target.value);
      valDistance.textContent = v;
      simulation.force('link').distance(v);
      simulation.alpha(0.25).restart();
    }});

    const sliderCollide = document.getElementById('slider-collide');
    const valCollide = document.getElementById('val-collide');
    sliderCollide.addEventListener('input', (e) => {{
      const v = parseFloat(e.target.value);
      valCollide.textContent = v;
      simulation.force('collide').radius(d => d.radius + v);
      simulation.alpha(0.25).restart();
    }});

    const sliderEdgeOp = document.getElementById('slider-edge-op');
    const valEdgeOp = document.getElementById('val-edge-op');
    sliderEdgeOp.addEventListener('input', (e) => {{
      const v = parseFloat(e.target.value);
      valEdgeOp.textContent = v.toFixed(2);
      edgeRestingOpacity = v;
      requestRender();
    }});

    const chkLod = document.getElementById('chk-lod');
    chkLod.addEventListener('change', (e) => {{
      enableSemanticLOD = e.target.checked;
      requestRender();
    }});

    // Global testing and programmatic API
    window.__repopeek = {{
      simulation,
      zoomBehavior,
      nodes: rawNodes,
      edges: rawEdges,
      nodeById,
      zoomTo: (targetK, targetX, targetY) => {{
        const cx = (targetX !== undefined) ? targetX : (width / 2);
        const cy = (targetY !== undefined) ? targetY : (height / 2);
        const newTransform = d3.zoomIdentity
          .translate(width / 2 - cx * targetK, height / 2 - cy * targetK)
          .scale(targetK);
        d3.select(canvas).call(zoomBehavior.transform, newTransform);
      }},
      spotlight: (nodeId) => {{
        const node = nodeById.get(nodeId);
        if (node) {{
          hoveredNode = node;
          hoverTransitionAlpha = 1.0;
          hoverName.textContent = node.signature || node.label;
          hoverBadge.textContent = node.kind || 'symbol';
          hoverBadge.style.background = node.comm_color + '33';
          hoverBadge.style.color = node.comm_color;
          hoverFile.textContent = node.file || 'internal';
          hoverDegree.textContent = node.degree;
          hoverIn.textContent = node.in_degree;
          hoverOut.textContent = node.out_degree;
          hoverBlast.textContent = node.blast_radius_count;
          hoverCard.style.display = 'block';
          hoverCard.style.left = (width / 2 + 20) + 'px';
          hoverCard.style.top = (height / 2 - 40) + 'px';
          requestRender();
        }}
      }},
      pin: (nodeId) => {{
        const node = nodeById.get(nodeId);
        if (node) pinNode(node);
      }},
      reset: () => {{
        hoveredNode = null;
        hoverTransitionAlpha = 0.0;
        hoverCard.style.display = 'none';
        pinNode(null);
        requestRender();
      }}
    }};
  </script>
</body>
</html>
"""

    return html_content


def export_html(
    graph: CanonicalGraph,
    out_file: Path,
    communities: Optional[Dict[int, List[str]]] = None,
    community_labels: Optional[Dict[int, str]] = None,
    max_nodes: int = 6000,
) -> Path:
    """Generate self-contained Obsidian-style interactive graph HTML."""
    out_path = Path(out_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = generate_html_content(
        graph=graph,
        communities=communities,
        community_labels=community_labels,
        max_nodes=max_nodes,
    )

    out_path.write_text(html_content, encoding="utf-8")

    alt_out = out_path.parent / "repopeek_graph.html"
    if alt_out != out_path:
        alt_out.write_text(html_content, encoding="utf-8")

    return out_path
