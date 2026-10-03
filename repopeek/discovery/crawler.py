"""Repository file discovery and deterministic scanner."""

import os
from pathlib import Path
from typing import Iterator, List, Literal, Optional
from pydantic import BaseModel, Field

from repopeek.config import RepopeekConfig
from repopeek.discovery.classifier import FileType, SUPPORTED_TYPES, classify_file, is_binary_file
from repopeek.discovery.hasher import compute_file_hashes
from repopeek.discovery.ignore import IgnoreRuleSet


class DiscoveredFile(BaseModel):
    """Metadata record for a discovered repository file."""
    path: Path = Field(description="Absolute file path on disk")
    rel_path: str = Field(description="Normalized POSIX relative path from repository root")
    file_type: FileType = Field(description="Classified file type")
    size_bytes: int = Field(ge=0, description="File size in bytes")
    is_binary: bool = Field(default=False, description="Whether file contains binary data")
    is_supported: bool = Field(default=True, description="Whether file type is supported for AST parsing")
    sha256: str = Field(description="SHA-256 of file content")
    blob_sha: str = Field(description="Git-compatible blob SHA")
    parse_status: Literal["pending", "ok", "error", "skipped_size", "skipped_binary", "unsupported"] = Field(
        default="pending", description="Initial parsing status"
    )


def discover_repository(
    repo_path: Path,
    config: Optional[RepopeekConfig] = None,
    ignore_rules: Optional[IgnoreRuleSet] = None,
) -> List[DiscoveredFile]:
    """Deterministically scan repository directory and return sorted list of files."""
    repo_root = repo_path.resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise ValueError(f"Target repository path '{repo_root}' does not exist or is not a directory.")

    if config is None:
        config = RepopeekConfig(repo_path=repo_root)

    if ignore_rules is None:
        ignore_rules = IgnoreRuleSet.from_ignore_file(repo_root)

    max_size_bytes = config.max_file_size_kb * 1024
    discovered: List[DiscoveredFile] = []

    for root, dirs, files in os.walk(repo_root, topdown=True):
        # Sort directories in-place for deterministic traversal order
        dirs.sort()
        # Filter out ignored directories
        dirs[:] = [
            d for d in dirs
            if not ignore_rules.is_dir_ignored(d)
            and not ignore_rules.is_path_ignored(Path(root) / d)
        ]

        files.sort()
        for filename in files:
            file_path = Path(root) / filename
            if ignore_rules.is_path_ignored(file_path):
                continue

            rel_posix = file_path.relative_to(repo_root).as_posix()
            file_type = classify_file(file_path)
            size_bytes = file_path.stat().st_size
            is_bin = is_binary_file(file_path) if size_bytes > 0 else False

            sha256, blob_sha = compute_file_hashes(file_path)

            # Determine initial parse status
            if is_bin:
                status = "skipped_binary"
                is_supported = False
            elif size_bytes > max_size_bytes:
                status = "skipped_size"
                is_supported = False
            elif file_type not in SUPPORTED_TYPES:
                status = "unsupported"
                is_supported = False
            else:
                status = "pending"
                is_supported = True

            discovered.append(
                DiscoveredFile(
                    path=file_path,
                    rel_path=rel_posix,
                    file_type=file_type,
                    size_bytes=size_bytes,
                    is_binary=is_bin,
                    is_supported=is_supported,
                    sha256=sha256,
                    blob_sha=blob_sha,
                    parse_status=status,
                )
            )

    return discovered
