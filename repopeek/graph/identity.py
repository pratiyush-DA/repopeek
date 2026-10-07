"""Canonical graph identity, language scoping, and display labels."""

from pathlib import Path
from typing import Optional, Tuple

PY_BUILTINS = frozenset({
    "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable", "chr",
    "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod",
    "enumerate", "eval", "exec", "filter", "float", "format", "frozenset",
    "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int",
    "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max",
    "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print",
    "property", "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars",
    "zip",
})

PY_STDLIB_ROOTS = frozenset({
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib",
    "copy", "csv", "dataclasses", "datetime", "decimal", "enum", "functools",
    "glob", "hashlib", "heapq", "http", "importlib", "inspect", "io", "itertools",
    "json", "logging", "math", "os", "pathlib", "pickle", "re", "shutil",
    "signal", "socket", "sqlite3", "string", "subprocess", "sys", "tempfile",
    "threading", "time", "typing", "unittest", "urllib", "uuid", "warnings",
    "weakref", "xml",
})

LANG_FROM_EXT = {
    ".py": "py",
    ".pyi": "py",
    ".ts": "ts",
    ".tsx": "ts",
    ".mts": "ts",
    ".cts": "ts",
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".sh": "sh",
    ".bash": "sh",
}

LANG_DISPLAY = {
    "py": "Python",
    "ts": "TypeScript",
    "js": "JavaScript",
    "sql": "SQL",
    "yaml": "YAML",
    "json": "JSON",
    "sh": "Shell",
    "ext": "external",
}

SQL_TABLE_KINDS = frozenset({"sql_table", "db_entity", "neo4j_label", "table"})
CONFIG_KINDS = frozenset({"json_config", "yaml_config"})


def language_from_node_id(node_id: str) -> str:
    """Return the language/runtime prefix of a canonical or external node id."""
    if not node_id:
        return ""
    if node_id.startswith("ext:"):
        parts = node_id.split(":")
        return parts[1] if len(parts) > 1 else ""
    if ":" in node_id:
        return node_id.split(":", 1)[0]
    return ""


def language_from_path(file_path: str) -> str:
    """Infer language code from a repository-relative file path."""
    if not file_path:
        return ""
    ext = Path(file_path).suffix.lower()
    return LANG_FROM_EXT.get(ext, "")


def infer_ecosystem(lang: str, name: str, edge_kind: str = "call") -> str:
    """Classify an unresolved name into builtin, stdlib, npm, or unresolved."""
    bare = name.split(".")[0].split("/")[0]
    if lang in ("ts", "js"):
        if edge_kind == "import" or "/" in name or name in ("next", "react", "axios"):
            return "npm"
        return "unresolved"
    if lang == "py":
        if bare in PY_BUILTINS:
            return "builtin"
        if bare in PY_STDLIB_ROOTS:
            return "stdlib"
        return "unresolved"
    return "unresolved"


def make_external_id(lang: str, name: str, edge_kind: str = "call") -> str:
    """Mint a language-scoped identity for an unresolved/external symbol."""
    lang = lang or "unk"
    eco = infer_ecosystem(lang, name, edge_kind)
    safe = name.replace("::", ".").strip() or "unknown"
    return f"ext:{lang}:{eco}:{safe}"


def is_sql_table_kind(kind: str) -> bool:
    return (kind or "").lower() in SQL_TABLE_KINDS


def is_config_kind(kind: str) -> bool:
    return (kind or "").lower() in CONFIG_KINDS


def format_node_label(
    node_id: str,
    kind: str = "",
    file_path: Optional[str] = None,
    sig: Optional[str] = None,
) -> str:
    """Human-readable developer label; never invent names not present in identity."""
    kind_l = (kind or "").lower()
    lang = language_from_node_id(node_id)
    lang_name = LANG_DISPLAY.get(lang, lang)

    if node_id.startswith("ext:"):
        parts = node_id.split(":")
        name = parts[-1] if parts else node_id
        eco = parts[2] if len(parts) > 2 else ""
        prefix = f"{lang_name}:{eco}" if eco else lang_name
        return f"{prefix}:{name}" if prefix else name

    qual = node_id.split("::")[-1] if "::" in node_id else node_id
    if qual in ("<module>", "<config>", "<script>", "<file>"):
        fname = Path(file_path).name if file_path else qual
        return f"module {fname}" if kind_l in ("file", "module", "") else f"{kind_l} {fname}"

    if kind_l in ("function", "method"):
        if sig and "(" in sig:
            short = sig.strip()
            if len(short) > 80:
                short = short[:77] + "..."
            return short
        return f"{kind_l} {qual}()"
    if kind_l == "class":
        return f"class {qual}"
    if lang_name:
        return f"{lang_name}: {qual}"
    return qual


def split_lang_and_name(node_id: str) -> Tuple[str, str]:
    return language_from_node_id(node_id), node_id.split("::")[-1] if "::" in node_id else node_id
