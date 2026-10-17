"""Automated MCP configuration and agent steering rules installer.

Detects, patches, and configures both:
1. MCP server registrations for:
   - Cursor (~/.cursor/mcp.json or <workspace>/.cursor/mcp.json)
   - Claude Desktop (%APPDATA%/Claude/claude_desktop_config.json)
   - Windsurf (~/.codeium/windsurf/mcp_config.json)
   - Antigravity IDE (~/.gemini/config/mcp_config.json or <workspace>/.gemini/mcp_config.json)
   - VS Code (<workspace>/.vscode/mcp.json)

2. Master System Prompt & Steering Rules for:
   - Cursor (<workspace>/.cursor/rules/repopeek.mdc and <workspace>/.cursorrules)
   - Claude Code (<workspace>/CLAUDE.md)
   - Windsurf (<workspace>/.windsurf/rules/repopeek.md and <workspace>/.windsurfrules)
   - Antigravity IDE (<workspace>/.agents/rules/repopeek.md and ~/.gemini/config/rules/repopeek.md)
   - VS Code / GitHub Copilot (<workspace>/.github/copilot-instructions.md)
   - Universal Agent Standard (<workspace>/AGENTS.md)
"""

import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Optional


START_RULE_TAG = "<!-- REPOPEEK-RULES:START -->"
END_RULE_TAG = "<!-- REPOPEEK-RULES:END -->"


def generate_repopeek_system_prompt(client: str = "general") -> str:
    """Generate the canonical evidence-backed steering rule for coding agents.
    
    Includes the 4-tier Hybrid Decision Ladder discovered in empirical benchmarks:
    - Skip RepoPeek for trivial leaf changes (known files, single regex, typos) to avoid token framing overhead.
    - Call repopeek_lookup (<70 tokens) for quick symbol signatures before editing.
    - Call repopeek_context for multi-file features and unfamiliar code (-54% to -65% context tokens).
    - Call repopeek_resolve for ambiguous keywords.
    - Call repopeek_impact before modifying shared interfaces or public classes.
    """
    body = f"""{START_RULE_TAG}
# RepoPeek Code Intelligence Protocol

When the RepoPeek MCP server is configured in this repository, follow this evidence-based Hybrid Decision Ladder for all code navigation, search, and refactoring:

## 1. Hybrid Decision Ladder
- **Leaf / Single-File Edit (known file, regex tweak, typo, single localized function):**
  -> Open the file directly. Do NOT invoke RepoPeek tools on known leaf locations to avoid token framing overhead.
- **Symbol Contract Check:**
  -> Call `repopeek_lookup(query="<symbol>")` (<70 tokens) before editing to check signature, location, and blast radius.
- **Multi-File Feature, Unfamiliar Code, or New Component:**
  -> ALWAYS call `repopeek_context(task="<task>")` FIRST. It compiles AST slices, constraints, and change planning, cutting context tokens by 50-65% without reading 500-line raw files.
- **Unknown Keyword or Identifier Search:**
  -> Call `repopeek_resolve(query="<term>")` FIRST (code-first BM25 + AST ranking).
- **Modifying Shared Interfaces, Base Classes, or Public APIs:**
  -> ALWAYS call `repopeek_impact(target="<symbol>")` FIRST to inspect upstream/downstream blast radius across call hierarchies, registries, and decorators.
- **Post-Edit Graph Synchronization:**
  -> Run `repopeek --update <file>` for sub-50ms incremental property graph synchronization.

## 2. Exploration Directives
- Zero Blind Grep: Avoid raw recursive grepping across the repository.
- Surgical Spans Only: Read only the specific line ranges returned by RepoPeek context slices.
{END_RULE_TAG}"""

    if client.lower() in ("cursor", "mdc"):
        frontmatter = """---
description: RepoPeek Code Intelligence & Navigation Protocol
globs: *
alwaysApply: true
---
"""
        return f"{frontmatter}{body}"
    return body


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


def get_default_rule_paths(
    client: str,
    workspace_root: Optional[Path] = None,
    global_install: bool = False,
) -> List[Path]:
    """Resolve default system prompt rule file paths for a given client."""
    client = client.lower().strip()
    home = Path.home()
    root = (workspace_root or Path(".")).resolve()
    paths: List[Path] = []

    if client == "cursor":
        paths.append(root / ".cursor" / "rules" / "repopeek.mdc")
        paths.append(root / ".cursorrules")
        if global_install:
            paths.append(home / ".cursor" / "rules" / "repopeek.mdc")

    elif client == "claude":
        paths.append(root / "CLAUDE.md")
        if global_install:
            paths.append(home / ".claude" / "CLAUDE.md")

    elif client == "windsurf":
        paths.append(root / ".windsurf" / "rules" / "repopeek.md")
        paths.append(root / ".windsurfrules")

    elif client == "antigravity":
        paths.append(root / ".agents" / "rules" / "repopeek.md")
        paths.append(home / ".gemini" / "config" / "rules" / "repopeek.md")

    elif client == "vscode":
        paths.append(root / ".github" / "copilot-instructions.md")

    elif client in ("all", "agents", "universal"):
        paths.append(root / "AGENTS.md")

    return paths


def _inject_rules_into_file(file_path: Path, rule_content: str, backup: bool = True) -> Dict[str, Any]:
    """Safely inject rule block using idempotent boundary tags without clobbering existing content."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None

    if file_path.exists():
        if backup:
            timestamp = int(time.time())
            backup_path = file_path.with_name(f"{file_path.name}.bak.{timestamp}")
            shutil.copy2(file_path, backup_path)

        try:
            existing = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            return {
                "path": str(file_path),
                "status": "error",
                "message": f"Failed to read existing rule file: {exc}",
            }

        if START_RULE_TAG in existing and END_RULE_TAG in existing:
            pattern = re.compile(rf"{re.escape(START_RULE_TAG)}.*?{re.escape(END_RULE_TAG)}", re.DOTALL)
            updated = pattern.sub(rule_content.strip(), existing)
        else:
            sep = "\n\n" if existing.strip() else ""
            updated = f"{existing.rstrip()}{sep}{rule_content.strip()}\n"
    else:
        updated = f"{rule_content.strip()}\n"

    try:
        file_path.write_text(updated, encoding="utf-8")
        return {
            "path": str(file_path),
            "status": "success",
            "backup": str(backup_path) if backup_path else None,
        }
    except Exception as exc:
        return {
            "path": str(file_path),
            "status": "error",
            "message": f"Failed to write rule file: {exc}",
        }


def install_agent_rules(
    client: str,
    repo_path: Path = Path("."),
    rule_files: Optional[List[Path]] = None,
    backup: bool = True,
    global_install: bool = False,
) -> Dict[str, Any]:
    """Inject master system prompt rules into agent instruction files."""
    paths = rule_files if rule_files is not None else get_default_rule_paths(
        client, workspace_root=repo_path, global_install=global_install
    )

    if not paths:
        return {
            "client": client,
            "status": "skipped",
            "message": f"No default rule files defined for client: {client}",
            "files": [],
        }

    results: List[Dict[str, Any]] = []
    for p in paths:
        # Generate format-specific prompt (e.g. Cursor .mdc YAML frontmatter)
        client_tag = "cursor" if str(p).endswith(".mdc") else client
        prompt = generate_repopeek_system_prompt(client=client_tag)
        res = _inject_rules_into_file(p, prompt, backup=backup)
        results.append(res)

    all_success = all(r.get("status") == "success" for r in results)
    return {
        "client": client,
        "status": "success" if all_success else "partial",
        "files": results,
    }


def install_all_rules(
    repo_path: Path = Path("."),
    clients: Optional[List[str]] = None,
    backup: bool = True,
    global_install: bool = False,
) -> Dict[str, Any]:
    """Install master system prompt rules across all target clients plus universal AGENTS.md."""
    if clients is None or "all" in clients:
        target_clients = ["cursor", "claude", "windsurf", "antigravity", "vscode", "agents"]
    else:
        target_clients = list(clients)
        if "agents" not in target_clients:
            target_clients.append("agents")

    results: Dict[str, Any] = {}
    for c in target_clients:
        results[c] = install_agent_rules(
            c, repo_path=repo_path, backup=backup, global_install=global_install
        )
    return results


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
    install_rules: bool = True,
    global_install: bool = False,
) -> Dict[str, Any]:
    """Patch MCP configuration file and optionally inject agent steering rules."""
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

    mcp_result: Dict[str, Any] = {}
    try:
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        mcp_result = {
            "client": client,
            "status": "success",
            "path": str(config_path),
            "backup": str(backup_path) if backup_path else None,
            "entry": mcp_entry,
        }
    except Exception as exc:
        mcp_result = {
            "client": client,
            "status": "error",
            "path": str(config_path),
            "message": f"Failed to write config file: {exc}",
        }

    # Also install agent steering rules if requested
    if install_rules and mcp_result.get("status") == "success":
        rule_res = install_agent_rules(
            client, repo_path=repo_path, backup=backup, global_install=global_install
        )
        mcp_result["rules"] = rule_res

    return mcp_result


def install_all_clients(
    repo_path: Path = Path("."),
    clients: Optional[List[str]] = None,
    use_python_exec: bool = False,
    backup: bool = True,
    install_rules: bool = True,
    global_install: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Install MCP registration and master rules across all specified or detected clients."""
    if clients is None or "all" in clients:
        target_clients = ["cursor", "claude", "windsurf", "antigravity"]
    else:
        target_clients = clients

    results: Dict[str, Dict[str, Any]] = {}
    for c in target_clients:
        results[c] = install_mcp_config(
            c,
            repo_path=repo_path,
            use_python_exec=use_python_exec,
            backup=backup,
            install_rules=install_rules,
            global_install=global_install,
        )

    # If installing rules, ensure universal AGENTS.md in workspace is also updated
    if install_rules:
        results["agents"] = install_agent_rules(
            "agents", repo_path=repo_path, backup=backup, global_install=global_install
        )

    return results
