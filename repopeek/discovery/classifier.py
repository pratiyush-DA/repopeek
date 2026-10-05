"""File type classification and binary detection."""

from enum import Enum
from pathlib import Path
from typing import Optional, Set


class FileType(str, Enum):
    """Recognized file types for RepoPeek intelligence engine."""
    PYTHON = "python"
    SQL = "sql"
    SHELL = "shell"
    JSON = "json"
    YAML = "yaml"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    OTHER = "other"


EXTENSION_MAP = {
    ".py": FileType.PYTHON,
    ".pyi": FileType.PYTHON,
    ".sql": FileType.SQL,
    ".sh": FileType.SHELL,
    ".bash": FileType.SHELL,
    ".json": FileType.JSON,
    ".yaml": FileType.YAML,
    ".yml": FileType.YAML,
    ".ts": FileType.TYPESCRIPT,
    ".tsx": FileType.TYPESCRIPT,
    ".mts": FileType.TYPESCRIPT,
    ".cts": FileType.TYPESCRIPT,
    ".js": FileType.JAVASCRIPT,
    ".jsx": FileType.JAVASCRIPT,
    ".mjs": FileType.JAVASCRIPT,
    ".cjs": FileType.JAVASCRIPT,
}

SUPPORTED_TYPES: Set[FileType] = {
    FileType.PYTHON,
    FileType.SQL,
    FileType.SHELL,
    FileType.JSON,
    FileType.YAML,
    FileType.TYPESCRIPT,
    FileType.JAVASCRIPT,
}


def is_binary_file(file_path: Path, sample_size: int = 8192) -> bool:
    """Check if file appears to be binary by scanning for null bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
            return b"\x00" in chunk
    except Exception:
        return True


def check_shebang(file_path: Path) -> Optional[FileType]:
    """Check first line for shell shebang if extension is absent or ambiguous."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#!"):
                if any(sh in first_line for sh in ("bash", "sh", "zsh", "dash")):
                    return FileType.SHELL
                if "python" in first_line:
                    return FileType.PYTHON
                if "node" in first_line:
                    return FileType.JAVASCRIPT
    except Exception:
        pass
    return None


def classify_file(file_path: Path) -> FileType:
    """Classify file by extension and shebang fallback."""
    suffix = file_path.suffix.lower()
    if suffix in EXTENSION_MAP:
        return EXTENSION_MAP[suffix]

    # Try shebang for executable scripts without extension
    shebang_type = check_shebang(file_path)
    if shebang_type is not None:
        return shebang_type

    return FileType.OTHER
