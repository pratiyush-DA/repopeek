"""Deterministic content and Git blob hashing utilities."""

import hashlib
from pathlib import Path
from typing import Tuple


def compute_hashes_from_bytes(data: bytes) -> Tuple[str, str]:
    """Compute (sha256, git_blob_sha) for raw byte payload.
    
    Git blob SHA is computed as: sha1("blob " + str(len(data)) + "\\0" + data).
    """
    sha256 = hashlib.sha256(data).hexdigest()
    
    # Standard git blob header
    header = f"blob {len(data)}\0".encode("utf-8")
    git_blob_sha = hashlib.sha1(header + data).hexdigest()
    
    return sha256, git_blob_sha


def compute_file_hashes(file_path: Path) -> Tuple[str, str]:
    """Read a local file and compute its SHA-256 and Git blob SHA."""
    content = file_path.read_bytes()
    return compute_hashes_from_bytes(content)
