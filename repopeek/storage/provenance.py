"""Git-anchored provenance extraction and blob hash tracking."""

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Dict, Optional

from repopeek.discovery.hasher import compute_file_hashes


@dataclass
class GitProvenance:
    """Audit origin metadata anchoring graph states to Git commits and blobs."""
    commit: Optional[str] = None
    branch: Optional[str] = None
    dirty: bool = False
    is_git: bool = False
    blob_shas: Dict[str, str] = field(default_factory=dict)


def get_git_provenance(repo_root: Path) -> GitProvenance:
    """Extract git commit SHA, branch, and dirty status with resilient non-git fallback."""
    root = Path(repo_root).resolve()

    try:
        # Check commit SHA
        commit_res = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if commit_res.returncode != 0 or not commit_res.stdout.strip():
            return GitProvenance(is_git=False)

        commit = commit_res.stdout.strip()

        # Check current branch
        branch_res = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        branch = branch_res.stdout.strip() if branch_res.returncode == 0 else None

        # Check dirty state (uncommitted / untracked changes)
        status_res = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        dirty = bool(status_res.stdout.strip()) if status_res.returncode == 0 else False

        return GitProvenance(
            commit=commit,
            branch=branch,
            dirty=dirty,
            is_git=True,
            blob_shas={},
        )
    except (FileNotFoundError, subprocess.SubprocessError, PermissionError):
        return GitProvenance(is_git=False)


def compute_repo_blob_shas(repo_root: Path, file_paths: list[Path]) -> Dict[str, str]:
    """Compute git blob SHAs for a collection of repository files."""
    root = Path(repo_root).resolve()
    blob_shas: Dict[str, str] = {}

    for file_path in file_paths:
        try:
            abs_p = file_path.resolve() if not file_path.is_absolute() else file_path
            rel_p = abs_p.relative_to(root).as_posix()
            _, blob_sha = compute_file_hashes(abs_p)
            blob_shas[rel_p] = blob_sha
        except (OSError, ValueError):
            continue

    return blob_shas
