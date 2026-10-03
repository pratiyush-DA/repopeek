"""Repository discovery, file classification, and hashing engine."""

from repopeek.discovery.classifier import (
    EXTENSION_MAP,
    SUPPORTED_TYPES,
    FileType,
    classify_file,
    is_binary_file,
)
from repopeek.discovery.crawler import DiscoveredFile, discover_repository
from repopeek.discovery.hasher import compute_file_hashes, compute_hashes_from_bytes
from repopeek.discovery.ignore import (
    DEFAULT_IGNORE_DIRS,
    DEFAULT_IGNORE_PATTERNS,
    IgnoreRuleSet,
)

__all__ = [
    "DEFAULT_IGNORE_DIRS",
    "DEFAULT_IGNORE_PATTERNS",
    "DiscoveredFile",
    "EXTENSION_MAP",
    "FileType",
    "IgnoreRuleSet",
    "SUPPORTED_TYPES",
    "classify_file",
    "compute_file_hashes",
    "compute_hashes_from_bytes",
    "discover_repository",
    "is_binary_file",
]
