"""File type classification, binary detection, and sensitive file shielding."""

import re
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
    # Phase 4 polyglot languages
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    SCALA = "scala"
    SWIFT = "swift"
    LUA = "lua"
    ZIG = "zig"
    POWERSHELL = "powershell"
    ELIXIR = "elixir"
    ERLANG = "erlang"
    FORTRAN = "fortran"
    JULIA = "julia"
    OBJC = "objc"
    VERILOG = "verilog"
    DART = "dart"
    TERRAFORM = "terraform"
    SOLIDITY = "solidity"
    GROOVY = "groovy"
    PASCAL = "pascal"
    VUE = "vue"
    SVELTE = "svelte"
    ASTRO = "astro"
    MARKDOWN = "markdown"
    OTHER = "other"


EXTENSION_MAP = {
    # Python
    ".py": FileType.PYTHON,
    ".pyi": FileType.PYTHON,
    ".pyw": FileType.PYTHON,
    # SQL
    ".sql": FileType.SQL,
    # Shell / Bash
    ".sh": FileType.SHELL,
    ".bash": FileType.SHELL,
    # JSON
    ".json": FileType.JSON,
    # YAML
    ".yaml": FileType.YAML,
    ".yml": FileType.YAML,
    # TypeScript
    ".ts": FileType.TYPESCRIPT,
    ".tsx": FileType.TYPESCRIPT,
    ".mts": FileType.TYPESCRIPT,
    ".cts": FileType.TYPESCRIPT,
    # JavaScript
    ".js": FileType.JAVASCRIPT,
    ".jsx": FileType.JAVASCRIPT,
    ".mjs": FileType.JAVASCRIPT,
    ".cjs": FileType.JAVASCRIPT,
    ".ejs": FileType.JAVASCRIPT,
    # Go
    ".go": FileType.GO,
    # Rust
    ".rs": FileType.RUST,
    # Java
    ".java": FileType.JAVA,
    # C
    ".c": FileType.C,
    ".h": FileType.C,
    # C++
    ".cpp": FileType.CPP,
    ".cc": FileType.CPP,
    ".cxx": FileType.CPP,
    ".hpp": FileType.CPP,
    ".cu": FileType.CPP,
    ".cuh": FileType.CPP,
    # C#
    ".cs": FileType.CSHARP,
    # Ruby
    ".rb": FileType.RUBY,
    ".rake": FileType.RUBY,
    # PHP
    ".php": FileType.PHP,
    # Kotlin
    ".kt": FileType.KOTLIN,
    ".kts": FileType.KOTLIN,
    # Scala
    ".scala": FileType.SCALA,
    # Swift
    ".swift": FileType.SWIFT,
    # Lua
    ".lua": FileType.LUA,
    ".luau": FileType.LUA,
    # Zig
    ".zig": FileType.ZIG,
    # PowerShell
    ".ps1": FileType.POWERSHELL,
    ".psm1": FileType.POWERSHELL,
    ".psd1": FileType.POWERSHELL,
    # Elixir
    ".ex": FileType.ELIXIR,
    ".exs": FileType.ELIXIR,
    # Erlang
    ".erl": FileType.ERLANG,
    ".hrl": FileType.ERLANG,
    # Fortran
    ".f": FileType.FORTRAN,
    ".f90": FileType.FORTRAN,
    ".f95": FileType.FORTRAN,
    ".f03": FileType.FORTRAN,
    ".f08": FileType.FORTRAN,
    # Julia
    ".jl": FileType.JULIA,
    # Objective-C
    ".m": FileType.OBJC,
    ".mm": FileType.OBJC,
    # Verilog / SystemVerilog
    ".v": FileType.VERILOG,
    ".sv": FileType.VERILOG,
    ".svh": FileType.VERILOG,
    # Dart
    ".dart": FileType.DART,
    # Terraform / HCL
    ".tf": FileType.TERRAFORM,
    ".tfvars": FileType.TERRAFORM,
    ".hcl": FileType.TERRAFORM,
    # Solidity
    ".sol": FileType.SOLIDITY,
    # Groovy
    ".groovy": FileType.GROOVY,
    ".gradle": FileType.GROOVY,
    # Pascal / Delphi
    ".pas": FileType.PASCAL,
    ".pp": FileType.PASCAL,
    ".dpr": FileType.PASCAL,
    ".lpr": FileType.PASCAL,
    # Vue
    ".vue": FileType.VUE,
    # Svelte
    ".svelte": FileType.SVELTE,
    # Astro
    ".astro": FileType.ASTRO,
    # Markdown
    ".md": FileType.MARKDOWN,
    ".mdx": FileType.MARKDOWN,
}

SUPPORTED_TYPES: Set[FileType] = {
    FileType.PYTHON,
    FileType.SQL,
    FileType.SHELL,
    FileType.JSON,
    FileType.YAML,
    FileType.TYPESCRIPT,
    FileType.JAVASCRIPT,
    # Phase 4 polyglot
    FileType.GO,
    FileType.RUST,
    FileType.JAVA,
    FileType.C,
    FileType.CPP,
    FileType.CSHARP,
    FileType.RUBY,
    FileType.PHP,
    FileType.KOTLIN,
    FileType.SCALA,
    FileType.SWIFT,
    FileType.LUA,
    FileType.ZIG,
    FileType.POWERSHELL,
    FileType.ELIXIR,
    FileType.ERLANG,
    FileType.FORTRAN,
    FileType.JULIA,
    FileType.OBJC,
    FileType.VERILOG,
    FileType.DART,
    FileType.TERRAFORM,
    FileType.SOLIDITY,
    FileType.GROOVY,
    FileType.PASCAL,
    FileType.VUE,
    FileType.SVELTE,
    FileType.ASTRO,
    FileType.MARKDOWN,
}


# Sensitive file patterns -- shield credentials and secrets from extraction
_SENSITIVE_PATTERNS = [
    re.compile(r'(^|[\\/])\.(env|envrc)(\.|$)', re.IGNORECASE),
    re.compile(r'\.(pem|key|p12|pfx|cert|crt|der|p8)$', re.IGNORECASE),
    re.compile(r'(^|[^A-Za-z0-9])(id_rsa|id_dsa|id_ecdsa|id_ed25519)(\.pub)?$', re.IGNORECASE),
    re.compile(r'^secring(\.(gpg|pgp))?$', re.IGNORECASE),
    re.compile(r'(\.netrc|\.pgpass|\.htpasswd|\.npmrc|\.pypirc|\.git-credentials|\.boto)$', re.IGNORECASE),
]

_ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist")


def is_sensitive_file(file_path: Path) -> bool:
    """Return True if the file likely contains secrets and should be skipped."""
    name = file_path.name
    # Committed dotenv templates are safe
    name_lower = name.lower()
    if any(name_lower.endswith(suf) for suf in _ENV_TEMPLATE_SUFFIXES):
        return False
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(name):
            return True
    return False


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
                if "ruby" in first_line:
                    return FileType.RUBY
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
