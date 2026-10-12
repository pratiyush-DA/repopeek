"""Automated MCP configuration installer for major AI coding assistants.

Detects and patches MCP configuration files for:
- Cursor (~/.cursor/mcp.json or <workspace>/.cursor/mcp.json)
- Claude Desktop (%APPDATA%/Claude/claude_desktop_config.json)
- Windsurf (~/.codeium/windsurf/mcp_config.json)
- Antigravity IDE (~/.gemini/config/mcp_config.json or <workspace>/.gemini/mcp_config.json)
- VS Code (<workspace>/.vscode/mcp.json)
"""

import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Dict, List, Optional


def get_default_config_path(client: str, workspace_root: Optional[Path] = None) -> Optional[Path]:
    """Resolve default MCP configuration file path for a given client."""
    client = client.lower().strip()
    home = Path.home()
    appdata = os.environ.get("APPDATA")

    if client == "cursor":
        if workspace_root and (workspace_root / ".cursor").exists():
            return workspace_root / ".cursor" / "mcp.json"
        return home / ".cursor" / "mcp.json"

    elif client == "claude":
        if os.name == "nt" and appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "darwin":
            return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            return home / ".config" / "Claude" / "claude_desktop_config.json"

    elif client == "windsurf":
        return home / ".codeium" / "windsurf" / "mcp_config.json"

    elif client == "antigravity":
        if workspace_root and (workspace_root / ".gemini").exists():
            return workspace_root / ".gemini" / "mcp_config.json"
        return home / ".gemini" / "config" / "mcp_config.json"

    elif client == "vscode":
        if workspace_root:
            return workspace_root / ".vscode" / "mcp.json"
        return home / ".vscode" / "mcp.json"

    return None


def generate_repopeek_mcp_entry(
    repo_path: Path,
    use_python_exec: bool = False,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate canonical MCP server registration payload for RepoPeek."""
    resolved_path = str(repo_path.resolve())
    if use_python_exec:
        cmd = sys.executable
        args = ["-m", "repopeek", "--serve-mcp", "--repo-path", resolved_path]
    else:
        cmd = "repopeek"
        args = ["--serve-mcp", "--repo-path", resolved_path]

    if extra_args:
        args.extend(extra_args)

    return {
        "command": cmd,
        "args": args,
    }


def install_mcp_config(
    client: str,
    repo_path: Path = Path("."),
    target_file: Optional[Path] = None,
    use_python_exec: bool = False,
    backup: bool = True,
) -> Dict[str, Any]:
    """Patch or create MCP configuration file for the target client."""
    config_path = target_file if target_file is not None else get_default_config_path(client, repo_path)
    if config_path is None:
        return {
            "client": client,
            "status": "error",
            "message": f"Unsupported or unresolvable client target: {client}",
        }

    config_path = Path(config_path)
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    backup_path = None
    data: Dict[str, Any] = {}

    if config_path.exists():
        if backup:
            timestamp = int(time.time())
            backup_path = config_path.with_name(f"{config_path.name}.bak.{timestamp}")
            shutil.copy2(config_path, backup_path)

        try:
            raw_text = config_path.read_text(encoding="utf-8")
            if raw_text.strip():
                data = json.loads(raw_text)
        except Exception as exc:
            return {
                "client": client,
                "status": "error",
                "path": str(config_path),
                "message": f"Failed to parse existing JSON config: {exc}",
            }

    # Standard format: {"mcpServers": { ... }}
    if "mcpServers" not in data or not isinstance(data.get("mcpServers"), dict):
        data["mcpServers"] = {}

    mcp_entry = generate_repopeek_mcp_entry(repo_path, use_python_exec=use_python_exec)
    data["mcpServers"]["repopeek"] = mcp_entry

    try:
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return {
            "client": client,
            "status": "success",
            "path": str(config_path),
            "backup": str(backup_path) if backup_path else None,
            "entry": mcp_entry,
        }
    except Exception as exc:
        return {
            "client": client,
            "status": "error",
            "path": str(config_path),
            "message": f"Failed to write config file: {exc}",
        }


def install_all_clients(
    repo_path: Path = Path("."),
    clients: Optional[List[str]] = None,
    use_python_exec: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Install MCP registration across all specified or detected clients."""
    if clients is None or "all" in clients:
        target_clients = ["cursor", "claude", "windsurf", "antigravity"]
    else:
        target_clients = clients

    results: Dict[str, Dict[str, Any]] = {}
    for c in target_clients:
        results[c] = install_mcp_config(c, repo_path=repo_path, use_python_exec=use_python_exec)

    return results
