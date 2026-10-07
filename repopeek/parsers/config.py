"""Deterministic JSON and YAML configuration parsers extracting structured keys and targets."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

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


def _flatten_config(data: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """Recursively flatten nested dictionary and list structures into dot-notated keys."""
    items: List[Tuple[str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)) and v:
                items.append((new_key, v))
                items.extend(_flatten_config(v, new_key))
            else:
                items.append((new_key, v))
    elif isinstance(data, list):
        for idx, elem in enumerate(data):
            new_key = f"{prefix}[{idx}]"
            if isinstance(elem, (dict, list)) and elem:
                items.append((new_key, elem))
                items.extend(_flatten_config(elem, new_key))
            else:
                items.append((new_key, elem))
    return items


class JsonConfigParser(BaseParser):
    """Parses JSON configuration files into canonical configuration keys and value links."""

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse JSON text into structured NodeCards and Edges with malformed error resilience."""
        norm_path = Path(rel_path).as_posix().lstrip("./")
        source_lines = source.splitlines()
        total_lines = max(1, len(source_lines))

        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        errors: List[str] = []

        file_id = NodeCard.make_id("json", norm_path, "<config>")
        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"json_config {norm_path}",
            span=Span(file=norm_path, start=1, end=total_lines),
            facts=NodeFacts(),
            story=NodeStory(text=f"JSON configuration file {norm_path}", source="deterministic", confidence="high"),
            content_hash=hash_content(source),
        )
        nodes.append(file_node)

        try:
            parsed = json.loads(source)
        except Exception as e:
            file_node.story.confidence = "unresolved"
            return ParseResult(
                file_path=Path(norm_path),
                rel_path=norm_path,
                language="json",
                nodes=nodes,
                edges=edges,
                errors=[f"JSONDecodeError in {norm_path}: {e}"],
            )

        flat_entries = _flatten_config(parsed)
        if len(flat_entries) > 80:
            file_node.facts.params = [k for k, _ in flat_entries[:20]]
            return ParseResult(
                file_path=Path(norm_path),
                rel_path=norm_path,
                language="json",
                nodes=nodes,
                edges=edges,
                errors=errors,
            )
        all_keys = [k for k, _ in flat_entries]
        file_node.facts.params = [k for k, v in flat_entries if not isinstance(v, (dict, list))]

        for key_path, val in flat_entries:
            key_id = NodeCard.make_id("json", norm_path, key_path)
            val_repr = json.dumps(val) if not isinstance(val, (dict, list)) else f"<{type(val).__name__}>"
            sig = f"{key_path} = {val_repr}"

            card = NodeCard(
                id=key_id,
                kind="json_config",
                sig=sig[:70],
                span=Span(file=norm_path, start=1, end=total_lines),
                facts=NodeFacts(reads=[val_repr] if not isinstance(val, (dict, list)) else []),
                story=NodeStory(
                    text=f"Config key `{key_path}` set to {val_repr}",
                    source="deterministic",
                    confidence="high",
                ),
                content_hash=hash_content(sig),
            )
            nodes.append(card)

            edges.append(
                Edge(
                    src=key_id,
                    dst=file_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(file=norm_path, start_line=1, end_line=total_lines, how_derived="json_key"),
                )
            )

        return ParseResult(
            file_path=Path(norm_path),
            rel_path=norm_path,
            language="json",
            nodes=nodes,
            edges=edges,
            errors=errors,
        )


class YamlConfigParser(BaseParser):
    """Parses YAML configuration files into canonical configuration keys and script references."""

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse YAML text into structured NodeCards and script links with error resilience."""
        norm_path = Path(rel_path).as_posix().lstrip("./")
        source_lines = source.splitlines()
        total_lines = max(1, len(source_lines))

        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        errors: List[str] = []

        file_id = NodeCard.make_id("yaml", norm_path, "<config>")
        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"yaml_config {norm_path}",
            span=Span(file=norm_path, start=1, end=total_lines),
            facts=NodeFacts(),
            story=NodeStory(text=f"YAML configuration file {norm_path}", source="deterministic", confidence="high"),
            content_hash=hash_content(source),
        )
        nodes.append(file_node)

        try:
            parsed = yaml.safe_load(source)
        except Exception as e:
            file_node.story.confidence = "unresolved"
            return ParseResult(
                file_path=Path(norm_path),
                rel_path=norm_path,
                language="yaml",
                nodes=nodes,
                edges=edges,
                errors=[f"YAMLError in {norm_path}: {e}"],
            )

        flat_entries = _flatten_config(parsed)
        file_node.facts.params = [k for k, v in flat_entries if not isinstance(v, (dict, list))]

        for key_path, val in flat_entries:
            key_id = NodeCard.make_id("yaml", norm_path, key_path)
            val_repr = str(val) if not isinstance(val, (dict, list)) else f"<{type(val).__name__}>"
            sig = f"{key_path}: {val_repr}"

            card = NodeCard(
                id=key_id,
                kind="yaml_config",
                sig=sig[:70],
                span=Span(file=norm_path, start=1, end=total_lines),
                facts=NodeFacts(reads=[val_repr] if not isinstance(val, (dict, list)) else []),
                story=NodeStory(
                    text=f"YAML config key `{key_path}`: {val_repr}",
                    source="deterministic",
                    confidence="high",
                ),
                content_hash=hash_content(sig),
            )
            nodes.append(card)

            edges.append(
                Edge(
                    src=key_id,
                    dst=file_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(file=norm_path, start_line=1, end_line=total_lines, how_derived="yaml_key"),
                )
            )

            # Detect if value points to an executable script (e.g. scripts/run_pipeline.sh)
            if isinstance(val, str) and (val.endswith(".sh") or val.endswith(".py")):
                edges.append(
                    Edge(
                        src=key_id,
                        dst=val.lstrip("./"),
                        type=EdgeType.RUNS_SCRIPT,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(file=norm_path, start_line=1, end_line=total_lines, how_derived="yaml_script_target"),
                    )
                )

        return ParseResult(
            file_path=Path(norm_path),
            rel_path=norm_path,
            language="yaml",
            nodes=nodes,
            edges=edges,
            errors=errors,
        )
