"""Minimal environment file (.env) parser without external dependencies."""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[Path] = None) -> bool:
    """Load key-value pairs from .env into os.environ if not already present."""
    if env_path is None:
        # Search current working directory and parent paths
        candidates = [Path.cwd() / ".env", Path(__file__).resolve().parent.parent.parent / ".env"]
        for cand in candidates:
            if cand.is_file():
                env_path = cand
                break

    if env_path is None or not env_path.is_file():
        return False

    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Strip quotes if wrapped
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
        return True
    except OSError:
        return False
