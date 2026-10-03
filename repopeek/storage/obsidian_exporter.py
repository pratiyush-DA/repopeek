"""Obsidian Markdown Vault exporter and reader for RepoPeek code graphs.

Exports a canonical code graph into an Obsidian vault containing atomic Markdown
notes with YAML frontmatter, bidirectional [[wikilinks]], and graph color groups.
Enables visual codebase exploration in Obsidian Desktop and consumption by AI agents.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from repopeek.models.schema import CanonicalGraph, NodeCard


def _sanitize_filename(name: str) -> str:
    """Sanitize identifier into a safe filename for Windows/macOS/Linux."""
    # Replace characters not allowed in filenames
    clean = re.sub(r'[\\/*?:"<>|]', "__", name)
    # Trim excessive length
    if len(clean) > 120:
        clean = clean[:110] + "_" + str(abs(hash(name)) % 10000)
    return clean


def _categorize_node(node: NodeCard) -> Tuple[str, str]:
    """Return (folder_name, note_basename) for a node."""
    kind = node.kind.lower()
    raw_id = node.id

    if kind in ("module", "file"):
        folder = "Modules"
        short_name = node.span.file if node.span else raw_id
        base = _sanitize_filename(short_name.replace("/", "__").replace("\\", "__"))
    elif kind in ("class", "interface", "struct"):
        folder = "Classes"
        short_name = raw_id.split("::")[-1]
        base = _sanitize_filename(short_name)
    elif kind in ("function", "method", "procedure"):
        folder = "Functions"
        short_name = raw_id.split("::")[-1]
        base = _sanitize_filename(short_name)
    elif kind in ("table", "entity", "model", "view", "database"):
        folder = "Entities"
        short_name = raw_id.split("::")[-1]
        base = _sanitize_filename(short_name)
    elif "config" in kind or "yaml" in kind or "json" in kind or "env" in kind:
        folder = "Configs"
        short_name = raw_id.split("::")[-1]
        base = _sanitize_filename(short_name)
    else:
        folder = "Symbols"
        short_name = raw_id.split("::")[-1]
        base = _sanitize_filename(short_name)

    return folder, base


def _is_exportable_node(node: NodeCard) -> bool:
    """Filter out fine-grained internal syntax tokens like leaf json/yaml keys and variables."""
    kind = node.kind.lower()
    if kind in ("variable", "token", "json_key", "yaml_key"):
        return False
    if "[" in node.id and "]" in node.id:
        return False
    if "config" in kind:
        # If it's a sub-property of a JSON file, filter it out
        if node.id.count("::") > 0:
            key_part = node.id.split("::")[-1]
            if "." in key_part or "[" in key_part:
                return False
    return True


def export_to_obsidian_vault(
    graph: CanonicalGraph,
    output_vault_dir: Path,
) -> Dict[str, Any]:
    """Export canonical graph into a structured Obsidian vault.
    
    Creates:
    - .obsidian/ configuration (app.json, graph.json with color groups)
    - 00 Overview.md index note
    - Categorized Markdown notes with YAML frontmatter and [[wikilinks]]
    """
    output_vault_dir = Path(output_vault_dir).resolve()
    output_vault_dir.mkdir(parents=True, exist_ok=True)

    # 1. Setup .obsidian config
    obsidian_dir = output_vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    app_json = {
        "legacyEditor": False,
        "livePreview": True,
        "newLinkFormat": "shortest",
        "showLineNumber": True,
        "showFrontmatter": True,
    }
    (obsidian_dir / "app.json").write_text(json.dumps(app_json, indent=2), encoding="utf-8")

    graph_json = {
        "collapse-filter": False,
        "search": "",
        "showTags": False,
        "showAttachments": False,
        "hideUnresolved": False,
        "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "path:Modules", "color": {"a": 1, "rgb": 7183615}},
            {"query": "path:Classes", "color": {"a": 1, "rgb": 15309489}},
            {"query": "path:Functions", "color": {"a": 1, "rgb": 8042491}},
            {"query": "path:Entities", "color": {"a": 1, "rgb": 16753995}},
            {"query": "path:Configs", "color": {"a": 1, "rgb": 16738957}},
        ],
    }
    (obsidian_dir / "graph.json").write_text(json.dumps(graph_json, indent=2), encoding="utf-8")

    # 2. Build node-to-note mapping and adjacency index for architectural nodes
    exportable_nodes = {nid: node for nid, node in graph.nodes.items() if _is_exportable_node(node)}
    node_to_note: Dict[str, str] = {}
    node_folder_map: Dict[str, str] = {}
    used_note_names: Set[str] = set()

    for nid, node in exportable_nodes.items():
        folder, base = _categorize_node(node)
        # Avoid collisions with O(1) set lookup
        candidate = base
        count = 1
        while candidate in used_note_names:
            candidate = f"{base}_{count}"
            count += 1
        node_to_note[nid] = candidate
        used_note_names.add(candidate)
        node_folder_map[nid] = folder

    outgoing_links: Dict[str, List[Tuple[str, str]]] = {nid: [] for nid in graph.nodes}
    incoming_links: Dict[str, List[Tuple[str, str]]] = {nid: [] for nid in graph.nodes}

    for edge in graph.edges:
        edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        if edge.src in node_to_note and edge.dst in node_to_note:
            dst_note = node_to_note[edge.dst]
            src_note = node_to_note[edge.src]
            outgoing_links[edge.src].append((dst_note, edge_type))
            incoming_links[edge.dst].append((src_note, edge_type))

    # 3. Create folders
    folders: Set[str] = set(node_folder_map.values())
    for f in folders:
        (output_vault_dir / f).mkdir(exist_ok=True)

    # 4. Generate note files
    exported_count = 0
    for nid, node in exportable_nodes.items():
        folder = node_folder_map[nid]
        note_name = node_to_note[nid]
        note_file = output_vault_dir / folder / f"{note_name}.md"

        frontmatter: Dict[str, Any] = {
            "id": node.id,
            "kind": node.kind,
            "file": node.span.file if node.span else None,
            "lines": f"{node.span.start}-{node.span.end}" if node.span else None,
            "complexity": node.facts.complexity if node.facts else 1,
            "tags": ["repopeek", "code-graph", node.kind.lower()],
        }

        # Build Markdown content
        lines = ["---"]
        for k, v in frontmatter.items():
            if v is not None:
                lines.append(f"{k}: {json.dumps(v)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {note_name}")
        lines.append(f"**Kind:** `{node.kind}` | **ID:** `{node.id}`")
        if node.span and node.span.file:
            lines.append(f"**Source:** `{node.span.file}:{node.span.start}-{node.span.end}`")
        lines.append("")

        if node.sig:
            lines.append("```python")
            lines.append(node.sig)
            lines.append("```")
            lines.append("")

        if node.story and node.story.text:
            lines.append("## Story")
            lines.append(f"> {node.story.text}")
            lines.append("")

        if node.facts:
            lines.append("## AST Facts")
            facts = node.facts
            lines.append(f"- **Complexity:** {facts.complexity}")
            lines.append(f"- **Direct Calls:** {facts.calls}")
            if facts.params:
                lines.append(f"- **Parameters:** {', '.join(facts.params)}")
            if facts.returns:
                lines.append(f"- **Returns:** `{facts.returns}`")
            if facts.raises:
                lines.append(f"- **Raises:** {', '.join(facts.raises)}")
            if facts.reads:
                lines.append(f"- **Reads:** {', '.join(facts.reads[:10])}")
            if facts.writes:
                lines.append(f"- **Writes:** {', '.join(facts.writes[:10])}")
            lines.append("")

        out_edges = outgoing_links.get(nid, [])
        if out_edges:
            lines.append("## Outgoing Dependencies")
            for target_note, rel_type in sorted(set(out_edges)):
                lines.append(f"- **{rel_type}** -> [[{target_note}]]")
            lines.append("")

        in_edges = incoming_links.get(nid, [])
        if in_edges:
            lines.append("## Incoming Callers & Usages")
            for caller_note, rel_type in sorted(set(in_edges)):
                lines.append(f"- **{rel_type}** <- [[{caller_note}]]")
            lines.append("")

        note_file.write_text("\n".join(lines), encoding="utf-8")
        exported_count += 1

    # 5. Create 00 Overview.md
    commit_str = getattr(graph, "repo_commit", None) or "unknown"
    overview_lines = [
        "---",
        "id: 00-overview",
        "title: RepoPeek Code Intelligence Graph",
        "tags: [repopeek, hub, index]",
        "---",
        "",
        "# RepoPeek Code Intelligence Graph",
        "",
        f"**Indexed Nodes:** {len(graph.nodes)} | **Indexed Relationships:** {len(graph.edges)}",
        f"**Repository Commit:** `{commit_str}`",
        "",
        "## Sub-Graph Categories",
        "- **[[Modules]]:** Source code files, packages, and scripts.",
        "- **[[Classes]]:** Object-oriented classes, protocols, and data models.",
        "- **[[Functions]]:** Functions, methods, and entry points.",
        "- **[[Entities]]:** Database tables, schema structures, and persistent entities.",
        "- **[[Configs]]:** Configuration settings, environment variables, and parameters.",
        "",
        "## Top Modules",
    ]
    for nid, node in graph.nodes.items():
        if node.kind.lower() in ("module", "file"):
            nname = node_to_note[nid]
            overview_lines.append(f"- [[{nname}]] (`{node.span.file if node.span else nid}`)")

    (output_vault_dir / "00 Overview.md").write_text("\n".join(overview_lines), encoding="utf-8")

    return {
        "vault_dir": str(output_vault_dir),
        "exported_notes": exported_count,
        "categories": list(folders),
    }


def read_obsidian_node(vault_dir: Path, symbol_or_name: str) -> Optional[Dict[str, Any]]:
    """Lookup and read an exported documentation note from an Obsidian vault."""
    vault_dir = Path(vault_dir).resolve()
    if not vault_dir.exists():
        return None

    target = _sanitize_filename(symbol_or_name.split("::")[-1])
    # Search across subdirectories
    for md_file in vault_dir.rglob("*.md"):
        if md_file.stem.lower() == target.lower() or target.lower() in md_file.stem.lower():
            content = md_file.read_text(encoding="utf-8")
            frontmatter: Dict[str, Any] = {}
            body = content

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        import yaml
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except Exception:
                        for line in parts[1].splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                frontmatter[k.strip()] = v.strip().strip('"')
                    body = parts[2].strip()

            # Extract [[wikilinks]]
            wikilinks = re.findall(r"\[\[(.*?)\]\]", body)

            return {
                "file": str(md_file.relative_to(vault_dir)),
                "name": md_file.stem,
                "frontmatter": frontmatter,
                "wikilinks": wikilinks,
                "body": body,
            }

    return None


def find_default_obsidian_vault() -> Optional[Path]:
    """Auto-detect the user's primary active Obsidian vault from Obsidian's local config.

    Inspects %APPDATA%/obsidian/obsidian.json on Windows,
    ~/Library/Application Support/obsidian/obsidian.json on macOS,
    and ~/.config/obsidian/obsidian.json on Linux.
    """
    import os
    import sys

    config_path = None
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            config_path = Path(appdata) / "obsidian" / "obsidian.json"
    elif sys.platform == "darwin":
        config_path = Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json"
    else:
        config_path = Path.home() / ".config" / "obsidian" / "obsidian.json"

    if not config_path or not config_path.exists():
        return None

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        vaults = data.get("vaults", {})
        # 1. Prefer vault currently marked as open
        for v in vaults.values():
            if v.get("open") and v.get("path"):
                p = Path(v["path"])
                if p.exists():
                    return p
        # 2. Fallback to most recently accessed vault
        sorted_vaults = sorted(vaults.values(), key=lambda x: x.get("ts", 0), reverse=True)
        for v in sorted_vaults:
            if v.get("path"):
                p = Path(v["path"])
                if p.exists():
                    return p
    except Exception:
        pass

    return None


def open_in_obsidian(target_path: Path) -> bool:
    """Open a folder or vault directly in Obsidian Desktop using the obsidian:// URI scheme."""
    import urllib.parse
    import webbrowser

    resolved = Path(target_path).resolve()
    # Official Obsidian URL scheme
    url = f"obsidian://open?path={urllib.parse.quote(str(resolved))}"
    try:
        return webbrowser.open(url)
    except Exception:
        return False

