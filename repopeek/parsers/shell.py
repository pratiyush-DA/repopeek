"""Deterministic Shell script parser extracting commands, scripts, and environment variables."""

import re
import shlex
from pathlib import Path
from typing import List, Optional, Set, Tuple

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

ENV_ASSIGN_RE = re.compile(r"^\s*(?:export\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)$")
ENV_READ_RE = re.compile(r"\$(?:\{([a-zA-Z_][a-zA-Z0-9_]*)\}|([a-zA-Z_][a-zA-Z0-9_]*))")
SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".pl", ".rb", ".js", ".ts"}
RUNNER_COMMANDS = {"python", "python3", "bash", "sh", "node", "perl", "ruby"}


class ShellParser(BaseParser):
    """Parses shell scripts into canonical command nodes, script runs, and env references."""

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse shell script line-by-line using standard library shlex and regex."""
        norm_path = Path(rel_path).as_posix().lstrip("./")
        source_lines = source.splitlines()
        total_lines = max(1, len(source_lines))

        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        errors: List[str] = []

        all_env_reads: Set[str] = set()
        all_env_writes: Set[str] = set()
        all_commands: List[str] = []
        all_script_targets: Set[str] = set()

        file_id = NodeCard.make_id("sh", norm_path, "<script>")

        # Process lines
        for idx, line in enumerate(source_lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check environment variable reads ($VAR or ${VAR})
            for m in ENV_READ_RE.finditer(stripped):
                var_name = m.group(1) or m.group(2)
                if var_name:
                    all_env_reads.add(var_name)

            # Check environment variable assignments (VAR=val or export VAR=val)
            assign_m = ENV_ASSIGN_RE.match(stripped)
            if assign_m:
                var_name = assign_m.group(1)
                all_env_writes.add(var_name)

            # Parse line into shlex tokens
            try:
                line_tokens = shlex.split(stripped, comments=True)
            except ValueError as ve:
                line_tokens = stripped.split()
                errors.append(f"shlex warning line {idx}: {ve}")

            if not line_tokens:
                continue

            # Group tokens by command separators (pipe, semicolon, and-operator)
            command_groups: List[List[str]] = []
            curr_cmd: List[str] = []
            for tok in line_tokens:
                if tok in ("|", ";", "&&", "||"):
                    if curr_cmd:
                        command_groups.append(curr_cmd)
                        curr_cmd = []
                else:
                    curr_cmd.append(tok)
            if curr_cmd:
                command_groups.append(curr_cmd)

            for seg_idx, tokens in enumerate(command_groups, start=1):
                if not tokens:
                    continue

                cmd_name = tokens[0]
                all_commands.append(cmd_name)

                # Check for executed scripts
                script_target = self._extract_script_target(tokens)
                if script_target:
                    all_script_targets.add(script_target)

                seg_suffix = f"_{seg_idx}" if len(command_groups) > 1 else ""
                cmd_id = NodeCard.make_id("sh", norm_path, f"cmd_L{idx}{seg_suffix}")
                cmd_sig = " ".join(tokens)[:60]

                cmd_card = NodeCard(
                    id=cmd_id,
                    kind="command",
                    sig=cmd_sig,
                    span=Span(file=norm_path, start=idx, end=idx),
                    facts=NodeFacts(
                        calls=1,
                        reads=sorted(list(all_env_reads)),
                        writes=sorted(list(all_env_writes)),
                        params=tokens[1:],
                    ),
                    story=NodeStory(
                        text=f"Shell command `{cmd_name}`" + (f" running {script_target}" if script_target else ""),
                        source="deterministic",
                        confidence="high",
                    ),
                    content_hash=hash_content(cmd_sig),
                )
                nodes.append(cmd_card)

                # DEFINED_IN edge
                edges.append(
                    Edge(
                        src=cmd_id,
                        dst=file_id,
                        type=EdgeType.DEFINED_IN,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=norm_path,
                            start_line=idx,
                            end_line=idx,
                            how_derived="shell_command",
                        ),
                    )
                )

                # RUNS_SCRIPT edge
                if script_target:
                    edges.append(
                        Edge(
                            src=cmd_id,
                            dst=script_target,
                            type=EdgeType.RUNS_SCRIPT,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=norm_path,
                                start_line=idx,
                                end_line=idx,
                                how_derived="shell_script_run",
                            ),
                        )
                    )

        # File Node
        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"shell_script {norm_path}",
            span=Span(file=norm_path, start=1, end=total_lines),
            facts=NodeFacts(
                calls=len(all_commands),
                reads=sorted(list(all_env_reads)),
                writes=sorted(list(all_env_writes)),
            ),
            story=NodeStory(
                text=f"Shell script with {len(all_commands)} commands and {len(all_script_targets)} script targets",
                source="deterministic",
                confidence="high",
            ),
            content_hash=hash_content(source),
        )
        nodes.insert(0, file_node)

        # File-level WRITES / READS edges
        for var in all_env_writes:
            edges.append(
                Edge(
                    src=file_id,
                    dst=var,
                    type=EdgeType.WRITES,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(file=norm_path, start_line=1, end_line=total_lines, how_derived="shell_env_export"),
                )
            )

        return ParseResult(
            file_path=Path(norm_path),
            rel_path=norm_path,
            language="shell",
            nodes=nodes,
            edges=edges,
            errors=errors,
        )

    def _extract_script_target(self, tokens: List[str]) -> Optional[str]:
        """Detect if command invokes a local script file."""
        if not tokens:
            return None

        cmd = tokens[0]
        # Direct execution: ./run.sh, scripts/test.sh
        if cmd.startswith("./") or cmd.endswith(tuple(SCRIPT_EXTENSIONS)):
            return cmd.lstrip("./")

        # Interpreter execution: python src/billing/invoice.py
        if cmd in RUNNER_COMMANDS and len(tokens) > 1:
            for arg in tokens[1:]:
                if not arg.startswith("-") and any(arg.endswith(ext) for ext in SCRIPT_EXTENSIONS):
                    return arg.lstrip("./")
        return None
