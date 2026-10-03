"""Base parser abstractions for RepoPeek deterministic code parsing engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from repopeek.models.schema import Edge, NodeCard


@dataclass
class ParseResult:
    """Result of parsing a single source file into canonical nodes and edges."""
    file_path: Path
    rel_path: str
    language: str
    nodes: List[NodeCard] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """True if parsed with zero fatal errors."""
        return len(self.errors) == 0


class BaseParser(ABC):
    """Abstract base class for all language-specific AST and dialect parsers."""

    @abstractmethod
    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse source code string into canonical nodes and edges."""
        pass

    def parse_file(
        self,
        file_path: Path,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Read and parse a file from disk."""
        resolved_path = Path(file_path).resolve()
        if repo_root:
            try:
                rel_path = resolved_path.relative_to(Path(repo_root).resolve()).as_posix()
            except ValueError:
                rel_path = resolved_path.as_posix()
        else:
            try:
                rel_path = resolved_path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                rel_path = resolved_path.as_posix()

        try:
            with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            return self.parse_source(source=source, rel_path=rel_path, repo_root=repo_root)
        except Exception as e:
            return ParseResult(
                file_path=resolved_path,
                rel_path=rel_path,
                language="unknown",
                errors=[f"File read error: {e}"],
            )
