"""Ignore rule parsing and path filtering for repository traversal."""

import fnmatch
from pathlib import Path
from typing import List, Optional, Set

DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".obsidian",
}

DEFAULT_IGNORE_PATTERNS: List[str] = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "Thumbs.db",
    "*.egg-info",
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
]


class IgnoreRuleSet:
    """Manages directory and pattern ignore rules."""

    def __init__(
        self,
        base_dir: Path,
        custom_patterns: Optional[List[str]] = None,
        ignore_dirs: Optional[Set[str]] = None,
    ):
        self.base_dir = base_dir.resolve()
        self.ignore_dirs = set(DEFAULT_IGNORE_DIRS) if ignore_dirs is None else set(ignore_dirs)
        self.patterns = list(DEFAULT_IGNORE_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)

    @classmethod
    def from_ignore_file(cls, base_dir: Path, ignore_file_name: str = ".repopeekignore") -> "IgnoreRuleSet":
        """Load ignore rules from a file in base_dir if it exists."""
        rules = cls(base_dir)
        ignore_file = base_dir / ignore_file_name
        if ignore_file.is_file():
            with open(ignore_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        rules.patterns.append(line)
        return rules

    def is_dir_ignored(self, dir_name: str) -> bool:
        """Check if directory name matches default ignore directories."""
        return dir_name in self.ignore_dirs

    def is_path_ignored(self, file_path: Path) -> bool:
        """Check if path matches any ignore pattern or directory."""
        try:
            rel_path = file_path.resolve().relative_to(self.base_dir)
        except ValueError:
            rel_path = file_path

        # Check path parts against ignore dirs
        for part in rel_path.parts:
            if part in self.ignore_dirs:
                return True

        # Check glob patterns against relative POSIX path, filename, and sub-parts
        posix_rel = rel_path.as_posix()
        file_name = file_path.name

        for raw_pattern in self.patterns:
            pattern = raw_pattern.rstrip("/")
            if (
                fnmatch.fnmatch(file_name, pattern)
                or fnmatch.fnmatch(posix_rel, pattern)
                or fnmatch.fnmatch(posix_rel, f"{pattern}/*")
                or any(fnmatch.fnmatch(part, pattern) for part in rel_path.parts)
            ):
                return True

        return False
