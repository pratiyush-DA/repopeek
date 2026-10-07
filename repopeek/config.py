"""Configuration settings and defaults for Repopeek."""

from pathlib import Path
from typing import List, Optional
import json
from pydantic import BaseModel, Field


class RepopeekConfig(BaseModel):
    """Configuration settings for repository analysis and graph construction."""

    repo_path: Path = Field(
        default_factory=lambda: Path("."),
        description="Path to the target repository root to analyze",
    )
    supported_extensions: List[str] = Field(
        default=[".py", ".sql", ".sh", ".bash", ".json", ".yaml", ".yml", ".ts", ".tsx", ".js", ".jsx"],
        description="File extensions supported for deterministic parsing",
    )
    output_dir: Path = Field(
        default_factory=lambda: Path("./output"),
        description="Directory where the generated graph and analysis artifacts are saved",
    )
    graph_filename: str = Field(
        default="graph.json",
        description="Output filename for the serialized property graph",
    )
    sql_dialect: str = Field(
        default="oracle",
        description="SQL dialect for AST parsing (e.g., oracle, postgres, ansi)",
    )
    max_file_size_kb: int = Field(
        default=2048,
        description="Maximum file size in KB to parse deterministically",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity level",
    )

    @property
    def graph_output_path(self) -> Path:
        """Returns the full resolved path to the graph output file."""
        return self.output_dir / self.graph_filename

    @classmethod
    def from_json_file(cls, filepath: Path) -> "RepopeekConfig":
        """Load configuration from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_json_file(self, filepath: Path) -> None:
        """Serialize configuration to a JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
