"""Deterministic TypeScript and JavaScript parser for RepoPeek property graph."""

import bisect
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from repopeek.discovery.hasher import hash_content
from repopeek.models.schema import (
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    NodeFacts,
    NodeStory,
    Span,
)
from repopeek.parsers.base import BaseParser, ParseResult

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

JSDOC_RE = re.compile(r"/\*\*([\s\S]*?)\*/")

# Imports & Exports
IMPORT_FROM_RE = re.compile(
    r"\bimport\s+(?:type\s+)?(.*?)\s+from\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE | re.DOTALL,
)
IMPORT_BARE_RE = re.compile(r"\bimport\s*['\"]([^'\"]+)['\"]")
REQUIRE_RE = re.compile(
    r"(?:const|let|var)\s+(?:\{([^}]+)\}|([a-zA-Z_$][a-zA-Z0-9_$]*))\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)"
)
DYNAMIC_IMPORT_RE = re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
EXPORT_FROM_RE = re.compile(
    r"\bexport\s+(?:type\s+)?(?:\{([^}]+)\}|\*)\s+from\s*['\"]([^'\"]+)['\"]"
)

# Classes & Interfaces
CLASS_DEF_RE = re.compile(
    r"\b(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)"
    r"(?:<[^>]+>)?"
    r"(?:\s+extends\s+([a-zA-Z_$][a-zA-Z0-9_$.<>\s]+?))?"
    r"(?:\s+implements\s+([^{]+))?\s*\{"
)
INTERFACE_DEF_RE = re.compile(
    r"\b(?:export\s+)?interface\s+([a-zA-Z_$][a-zA-Z0-9_$]*)(?:<[^>]+>)?(?:\s+extends\s+([^{]+))?\s*\{"
)
TYPE_ALIAS_RE = re.compile(
    r"\b(?:export\s+)?type\s+([a-zA-Z_$][a-zA-Z0-9_$]*)(?:<[^>]+>)?\s*=\s*([^;]+);"
)

# Functions
FUNC_DEF_RE = re.compile(
    r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function(?:\s*\*)?\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*"
    r"(?:<[^>]+>)?\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*\{"
)
ARROW_FUNC_RE = re.compile(
    r"\b(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*"
    r"(?::\s*[^=]+)?\s*=\s*(?:async\s+)?(?:\(([^)]*)\)|([a-zA-Z_$][a-zA-Z0-9_$]*))\s*"
    r"(?::\s*([^=]+))?\s*=>\s*(\{?)"
)
FUNC_EXPR_RE = re.compile(
    r"\b(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*"
    r"(?::\s*[^=]+)?\s*=\s*(?:async\s+)?function(?:\s*\*)?\s*"
    r"(?:<[^>]+>)?\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*\{"
)
# Arrow function wrapped in a React hook / HOC, e.g.
#   const login = useCallback(async (email, password) => { ... }, [])
#   const Row = memo(({ item }) => { ... })
# ARROW_FUNC_RE cannot see these because a call expression sits between '=' and '=>'.
WRAPPED_ARROW_RE = re.compile(
    r"\b(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*"
    r"(?:React\.)?(?:useCallback|useMemo|memo|forwardRef)\s*(?:<[^>]*>)?\s*\(\s*"
    r"(?:async\s+)?(?:\(([^)]*)\)|([a-zA-Z_$][a-zA-Z0-9_$]*))\s*(?::[^=]+?)?=>\s*\{"
)
# Module-level SCREAMING_SNAKE_CASE constants (API_BASE_URL, REMEMBER_ME_DAYS, …) that
# tasks frequently reference. Scoped to all-caps names to stay bounded and avoid emitting
# a node for every local variable.
CONST_DECL_RE = re.compile(
    r"\b(?:export\s+)?const\s+([A-Z][A-Z0-9_]{2,})\s*(?::\s*[^=;]+)?=\s*([^;\n]+)"
)

# Method inside class body (captures entire declaration in group 1, method name in group 2)
METHOD_DEF_RE = re.compile(
    r"(?:^|[;\n}])\s*((?:(?:public|private|protected|static|async|get|set|readonly)\s+)*"
    r"(constructor|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*"
    r"(?:<[^>]+>)?\s*\(([^)]*)\)(?:\s*:\s*([^{;]+))?\s*\{)"
)

# Calls & Invariants
CALL_PATTERN = re.compile(r"\b([a-zA-Z_$][a-zA-Z0-9_$]*(?:\.[a-zA-Z_$][a-zA-Z0-9_$]*)*)\s*\(")
JS_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "function", "return", "throw",
    "typeof", "instanceof", "new", "import", "super", "require", "case", "default"
}
THROW_RE = re.compile(r"\bthrow\s+(?:new\s+)?([a-zA-Z0-9_$]+)")
COMPLEXITY_RE = re.compile(r"\b(if|else\s+if|for|while|switch|case|catch)\b|\?\s*[^:]+\s*:|&&|\|\|")
HTTP_CALL_RE = re.compile(
    r"\b(?:fetch\s*\(\s*['\"`]([^'\"`]+)['\"`]"
    r"|(?:axios|apiClient)\.(get|post|put|delete|patch)\s*\(\s*['\"`]([^'\"`]+)['\"`]"
    r"|(?:axios|apiClient)\s*\(\s*['\"`]([^'\"`]+)['\"`])",
    re.IGNORECASE,
)


def _extract_http_calls(code: str, extra_wrappers: Optional[List[str]] = None) -> List[str]:
    """Extract client HTTP requests with optional HTTP methods and wrapper helpers."""
    reads = []
    for m in HTTP_CALL_RE.finditer(code):
        if m.group(1):
            reads.append(f"HTTP:{m.group(1)}")
        elif m.group(2) and m.group(3):
            reads.append(f"HTTP:{m.group(2).upper()}:{m.group(3)}")
        elif m.group(4):
            reads.append(f"HTTP:{m.group(4)}")
    if extra_wrappers:
        names = [n for n in extra_wrappers if n and n not in ("fetch", "if", "for")]
        if names:
            alt = "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True))
            wr = re.compile(
                rf"\b(?:{alt})\s*(?:<[^>]*>)?\s*\(\s*['\"`]([^'\"`]+)['\"`]",
                re.IGNORECASE,
            )
            for m in wr.finditer(code):
                url = m.group(1)
                if url.startswith("/") or url.startswith("http") or "/api" in url.lower():
                    tag = f"HTTP:{url}"
                    if tag not in reads:
                        reads.append(tag)
    return reads


def _looks_like_http_client_impl(code: str) -> bool:
    if not code:
        return False
    return bool(
        HTTP_CALL_RE.search(code)
        or re.search(r"\b(?:fetch|axios)\s*\(", code)
        or re.search(r"\baxios\.(get|post|put|delete|patch)\s*\(", code)
    )


def _propagate_http_wrapper_calls(nodes: List[NodeCard], source: str = "") -> None:
    """If a function wraps fetch/axios, treat its callers' URL arguments as HTTP calls."""
    wrappers: List[str] = []
    for n in nodes:
        if n.kind not in ("function", "method"):
            continue
        body = n.snippet or ""
        if any(r.startswith("HTTP:") for r in n.facts.reads) or _looks_like_http_client_impl(body):
            name = n.id.split("::")[-1].split(".")[-1]
            if name and name not in ("fetch", "axios"):
                wrappers.append(name)
    if source:
        for m in re.finditer(
            r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\(",
            source,
        ):
            name = m.group(1)
            window = source[m.start() : m.start() + 900]
            if name not in ("fetch", "axios") and _looks_like_http_client_impl(window):
                wrappers.append(name)
    wrappers = list(dict.fromkeys(wrappers))
    if not wrappers:
        return
    for n in nodes:
        if n.kind not in ("function", "method") or not n.snippet:
            continue
        extra = _extract_http_calls(n.snippet, wrappers)
        for tag in extra:
            if tag not in n.facts.reads:
                n.facts.reads.append(tag)
        if _looks_like_http_client_impl(n.snippet) and not any(r.startswith("HTTP:") for r in n.facts.reads):
            n.facts.reads.append("HTTP:wrapper")


# ---------------------------------------------------------------------------
# Source Sanitization & Matching Helpers
# ---------------------------------------------------------------------------

def _build_line_starts(source: str) -> List[int]:
    """Index starting character offsets of lines for fast binary search."""
    return [0] + [m.end() for m in re.finditer(r"\n", source)]


def _get_line_number(line_starts: List[int], char_idx: int) -> int:
    """Return 1-indexed line number for character index in source."""
    return bisect.bisect_right(line_starts, char_idx)


def _sanitize_source(source: str) -> str:
    """Replace comments and string literals with spaces, preserving newlines and char offsets."""
    chars = list(source)
    n = len(chars)
    i = 0

    while i < n:
        c = chars[i]

        # Line comment: //
        if c == "/" and i + 1 < n and chars[i + 1] == "/":
            start = i
            while i < n and chars[i] != "\n":
                if chars[i] != "\r":
                    chars[i] = " "
                i += 1
            continue

        # Block comment: /* ... */
        if c == "/" and i + 1 < n and chars[i + 1] == "*":
            start = i
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            while i < n:
                if chars[i] == "*" and i + 1 < n and chars[i + 1] == "/":
                    chars[i] = " "
                    chars[i + 1] = " "
                    i += 2
                    break
                if chars[i] not in ("\n", "\r"):
                    chars[i] = " "
                i += 1
            continue

        # String literals: '...', "...", `...`
        if c in ("'", '"', "`"):
            quote = c
            chars[i] = " "
            i += 1
            while i < n:
                if chars[i] == "\\":
                    chars[i] = " "
                    if i + 1 < n and chars[i + 1] not in ("\n", "\r"):
                        chars[i + 1] = " "
                    i += 2
                    continue
                if chars[i] == quote:
                    chars[i] = " "
                    i += 1
                    break
                if chars[i] not in ("\n", "\r"):
                    chars[i] = " "
                i += 1
            continue

        i += 1

    return "".join(chars)


def _find_matching_brace(text: str, open_idx: int) -> int:
    """Find index of matching closing brace '}' for opening brace at open_idx."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def _extract_jsdoc_map(source: str, line_starts: List[int]) -> Dict[int, str]:
    """Map starting line of code blocks to their preceding JSDoc comment."""
    doc_map: Dict[int, str] = {}
    for m in JSDOC_RE.finditer(source):
        doc_start_line = _get_line_number(line_starts, m.start())
        doc_end_line = _get_line_number(line_starts, m.end())
        raw_lines = m.group(1).splitlines()
        cleaned_lines = []
        for line in raw_lines:
            stripped = line.strip().lstrip("*").strip()
            if stripped:
                cleaned_lines.append(stripped)
        if cleaned_lines:
            text = " ".join(cleaned_lines)
            if doc_start_line == 1:
                doc_map[1] = text
            for offset in range(0, 4):
                doc_map[doc_end_line + offset] = text
    return doc_map


def _parse_params(params_str: str) -> List[str]:
    """Parse comma-separated parameter list into clean parameter names."""
    if not params_str or not params_str.strip():
        return []
    raw_params = [p.strip() for p in params_str.split(",") if p.strip()]
    clean_params = []
    for p in raw_params:
        p_name = p.split(":")[0].strip()
        p_name = p_name.split("=")[0].strip()
        p_name = p_name.lstrip(".")  # rest param
        p_name = p_name.rstrip("?")  # optional param
        if p_name:
            clean_params.append(p_name)
    return clean_params


def _extract_calls_from_code(code: str, line_starts: List[int], base_offset: int, file_path: str) -> List[Tuple[str, int]]:
    """Extract (callee_name, line_num) calls from inside code block body."""
    calls: List[Tuple[str, int]] = []
    seen = set()
    for m in CALL_PATTERN.finditer(code):
        callee = m.group(1).strip()
        bare_callee = callee.split(".")[-1]
        if bare_callee in JS_KEYWORDS or callee in JS_KEYWORDS:
            continue
        line_num = _get_line_number(line_starts, base_offset + m.start())
        key = (callee, line_num)
        if key not in seen:
            seen.add(key)
            calls.append((callee, line_num))
    return calls


# ---------------------------------------------------------------------------
# TypeScript & JavaScript Parser
# ---------------------------------------------------------------------------

class TypeScriptParser(BaseParser):
    """Deterministic, resilient parser for TypeScript and JavaScript files."""

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse TS/JS source code into canonical NodeCards and typed Edges."""
        norm_path = Path(rel_path).as_posix().lstrip("./")
        source_lines = source.splitlines()
        total_lines = max(1, len(source_lines))

        ext = Path(norm_path).suffix.lower()
        is_ts = ext in (".ts", ".tsx", ".mts", ".cts")
        lang_code = "ts" if is_ts else "js"
        lang_name = "typescript" if is_ts else "javascript"

        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        errors: List[str] = []

        line_starts = _build_line_starts(source)
        jsdoc_map = _extract_jsdoc_map(source, line_starts)
        sanitized = _sanitize_source(source)

        file_id = NodeCard.make_id(lang_code, norm_path, "<module>")
        file_story = (
            f"TypeScript module {norm_path}"
            if is_ts
            else f"JavaScript module {norm_path}"
        )
        if 1 in jsdoc_map:
            file_story = jsdoc_map[1]

        file_node = NodeCard(
            id=file_id,
            kind="file",
            sig=f"module {norm_path}",
            span=Span(file=norm_path, start=1, end=total_lines),
            facts=NodeFacts(),
            story=NodeStory(text=file_story, source="deterministic", confidence="high"),
            content_hash=hash_content(source),
        )
        nodes.append(file_node)

        # -------------------------------------------------------------------
        # 1. Imports Extraction
        # -------------------------------------------------------------------
        for m in IMPORT_FROM_RE.finditer(source):
            specifiers = m.group(1).strip()
            target_module = m.group(2).strip()
            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, m.end())

            # Module-level import edge
            edges.append(
                Edge(
                    src=file_id,
                    dst=target_module,
                    type=EdgeType.IMPORTS,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_import",
                    ),
                )
            )

            # Specific named imports e.g. { foo, bar as baz }
            if "{" in specifiers and "}" in specifiers:
                named_block = specifiers[specifiers.find("{") + 1 : specifiers.find("}")]
                for sym in named_block.split(","):
                    sym = sym.strip()
                    if not sym:
                        continue
                    clean_sym = sym.split(" as ")[0].strip()
                    if clean_sym:
                        edges.append(
                            Edge(
                                src=file_id,
                                dst=f"{target_module}.{clean_sym}",
                                type=EdgeType.IMPORTS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=norm_path,
                                    start_line=start_line,
                                    end_line=end_line,
                                    how_derived="ts_import_symbol",
                                ),
                            )
                        )

        for m in IMPORT_BARE_RE.finditer(source):
            target_module = m.group(1).strip()
            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, m.end())
            edges.append(
                Edge(
                    src=file_id,
                    dst=target_module,
                    type=EdgeType.IMPORTS,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_import_bare",
                    ),
                )
            )

        for m in REQUIRE_RE.finditer(source):
            named = m.group(1)
            single = m.group(2)
            target_module = m.group(3).strip()
            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, m.end())
            edges.append(
                Edge(
                    src=file_id,
                    dst=target_module,
                    type=EdgeType.IMPORTS,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="js_require",
                    ),
                )
            )
            if named:
                for sym in named.split(","):
                    sym = sym.strip()
                    clean_sym = sym.split(":")[0].strip()
                    if clean_sym:
                        edges.append(
                            Edge(
                                src=file_id,
                                dst=f"{target_module}.{clean_sym}",
                                type=EdgeType.IMPORTS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=norm_path,
                                    start_line=start_line,
                                    end_line=end_line,
                                    how_derived="js_require_symbol",
                                ),
                            )
                        )

        # Dynamic imports
        for m in DYNAMIC_IMPORT_RE.finditer(source):
            target_module = m.group(1).strip()
            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, m.end())
            edges.append(
                Edge(
                    src=file_id,
                    dst=target_module,
                    type=EdgeType.IMPORTS,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="dynamic_import",
                    ),
                )
            )

        # -------------------------------------------------------------------
        # 2. Interfaces & Types Extraction
        # -------------------------------------------------------------------
        for m in INTERFACE_DEF_RE.finditer(sanitized):
            iface_name = m.group(1)
            bases_str = m.group(2)
            open_brace_idx = m.end() - 1
            close_brace_idx = _find_matching_brace(sanitized, open_brace_idx)

            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, close_brace_idx)
            iface_id = NodeCard.make_id(lang_code, norm_path, iface_name)
            iface_doc = jsdoc_map.get(start_line, f"Interface {iface_name}")

            raw_snippet = source[m.start() : close_brace_idx + 1]

            iface_card = NodeCard(
                id=iface_id,
                kind="interface",
                sig=f"interface {iface_name}",
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(),
                story=NodeStory(text=iface_doc, source="deterministic", confidence="high"),
                snippet=raw_snippet if len(raw_snippet) <= 1000 else raw_snippet[:1000] + "...",
                content_hash=hash_content(raw_snippet),
            )
            nodes.append(iface_card)

            edges.append(
                Edge(
                    src=file_id,
                    dst=iface_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_interface",
                    ),
                )
            )

            if bases_str:
                for base in bases_str.split(","):
                    base = base.strip()
                    if base:
                        edges.append(
                            Edge(
                                src=iface_id,
                                dst=base,
                                type=EdgeType.INHERITS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=norm_path,
                                    start_line=start_line,
                                    end_line=end_line,
                                    how_derived="ts_extends",
                                ),
                            )
                        )

        for m in TYPE_ALIAS_RE.finditer(sanitized):
            type_name = m.group(1)
            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, m.end())
            type_id = NodeCard.make_id(lang_code, norm_path, type_name)
            type_doc = jsdoc_map.get(start_line, f"Type alias {type_name}")

            raw_snippet = source[m.start() : m.end()]
            type_card = NodeCard(
                id=type_id,
                kind="type",
                sig=f"type {type_name}",
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(),
                story=NodeStory(text=type_doc, source="deterministic", confidence="high"),
                snippet=raw_snippet,
                content_hash=hash_content(raw_snippet),
            )
            nodes.append(type_card)
            edges.append(
                Edge(
                    src=file_id,
                    dst=type_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_type",
                    ),
                )
            )

        # -------------------------------------------------------------------
        # 3. Classes & Methods Extraction
        # -------------------------------------------------------------------
        for m in CLASS_DEF_RE.finditer(sanitized):
            class_name = m.group(1)
            base_class = m.group(2)
            implements_str = m.group(3)

            open_brace_idx = m.end() - 1
            close_brace_idx = _find_matching_brace(sanitized, open_brace_idx)

            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, close_brace_idx)
            class_id = NodeCard.make_id(lang_code, norm_path, class_name)
            class_doc = jsdoc_map.get(start_line, f"Class {class_name}")

            raw_class_snippet = source[m.start() : close_brace_idx + 1]

            class_card = NodeCard(
                id=class_id,
                kind="class",
                sig=f"class {class_name}" + (f" extends {base_class.strip()}" if base_class else ""),
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(),
                story=NodeStory(text=class_doc, source="deterministic", confidence="high"),
                snippet=raw_class_snippet if len(raw_class_snippet) <= 1500 else raw_class_snippet[:1500] + "...",
                content_hash=hash_content(raw_class_snippet),
            )
            nodes.append(class_card)

            edges.append(
                Edge(
                    src=file_id,
                    dst=class_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_class",
                    ),
                )
            )

            if base_class:
                edges.append(
                    Edge(
                        src=class_id,
                        dst=base_class.strip(),
                        type=EdgeType.INHERITS,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=norm_path,
                            start_line=start_line,
                            end_line=end_line,
                            how_derived="ts_extends",
                        ),
                    )
                )

            if implements_str:
                for iface in implements_str.split(","):
                    iface = iface.strip()
                    if iface:
                        edges.append(
                            Edge(
                                src=class_id,
                                dst=iface,
                                type=EdgeType.IMPLEMENTS,
                                confidence=Confidence.RESOLVED,
                                evidence=Evidence(
                                    file=norm_path,
                                    start_line=start_line,
                                    end_line=end_line,
                                    how_derived="ts_implements",
                                ),
                            )
                        )

            # Class methods scanning
            body_sanitized = sanitized[open_brace_idx + 1 : close_brace_idx]
            for mm in METHOD_DEF_RE.finditer(body_sanitized):
                method_decl_offset = open_brace_idx + 1 + mm.start(1)
                method_name = mm.group(2)
                method_params = mm.group(3)
                ret_type = mm.group(4).strip() if mm.group(4) else None

                method_open_brace = open_brace_idx + 1 + mm.end() - 1
                method_close_brace = _find_matching_brace(sanitized, method_open_brace)

                m_start_line = _get_line_number(line_starts, method_decl_offset)
                m_end_line = _get_line_number(line_starts, method_close_brace)

                method_id = NodeCard.make_id(lang_code, norm_path, f"{class_name}.{method_name}")
                method_doc = jsdoc_map.get(m_start_line, f"Method {class_name}.{method_name}")

                raw_method_code = source[method_decl_offset : method_close_brace + 1]
                method_body = source[method_open_brace + 1 : method_close_brace]

                parsed_params = _parse_params(method_params)
                raises_list = list(dict.fromkeys(THROW_RE.findall(method_body)))
                complexity_score = 1 + len(COMPLEXITY_RE.findall(method_body))

                method_calls = _extract_calls_from_code(
                    method_body,
                    line_starts,
                    method_open_brace + 1,
                    norm_path,
                )

                # HTTP reads
                http_reads = _extract_http_calls(method_body)

                method_card = NodeCard(
                    id=method_id,
                    kind="method",
                    sig=f"{method_name}({method_params.strip()})" + (f": {ret_type}" if ret_type else ""),
                    span=Span(file=norm_path, start=m_start_line, end=m_end_line),
                    facts=NodeFacts(
                        params=parsed_params,
                        returns=ret_type,
                        raises=raises_list,
                        complexity=complexity_score,
                        calls=len(method_calls),
                        reads=http_reads,
                    ),
                    story=NodeStory(text=method_doc, source="deterministic", confidence="high"),
                    snippet=raw_method_code if len(raw_method_code) <= 1500 else raw_method_code[:1500] + "...",
                    content_hash=hash_content(raw_method_code),
                )
                nodes.append(method_card)

                edges.append(
                    Edge(
                        src=class_id,
                        dst=method_id,
                        type=EdgeType.DEFINED_IN,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=norm_path,
                            start_line=m_start_line,
                            end_line=m_end_line,
                            how_derived="ts_method",
                        ),
                    )
                )

                for callee, call_line in method_calls:
                    edges.append(
                        Edge(
                            src=method_id,
                            dst=callee,
                            type=EdgeType.CALLS,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=norm_path,
                                start_line=call_line,
                                end_line=call_line,
                                how_derived="ts_call",
                            ),
                        )
                    )

        # -------------------------------------------------------------------
        # 4. Standalone Functions Extraction
        # -------------------------------------------------------------------
        for m in FUNC_DEF_RE.finditer(sanitized):
            func_name = m.group(1)
            params_str = m.group(2)
            ret_type = m.group(3).strip() if m.group(3) else None

            open_brace_idx = m.end() - 1
            close_brace_idx = _find_matching_brace(sanitized, open_brace_idx)

            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, close_brace_idx)
            func_id = NodeCard.make_id(lang_code, norm_path, func_name)
            func_doc = jsdoc_map.get(start_line, f"Function {func_name}")

            raw_func_code = source[m.start() : close_brace_idx + 1]
            func_body = source[open_brace_idx + 1 : close_brace_idx]

            parsed_params = _parse_params(params_str)
            raises_list = list(dict.fromkeys(THROW_RE.findall(func_body)))
            complexity_score = 1 + len(COMPLEXITY_RE.findall(func_body))

            func_calls = _extract_calls_from_code(
                func_body,
                line_starts,
                open_brace_idx + 1,
                norm_path,
            )

            http_reads = _extract_http_calls(func_body)

            func_card = NodeCard(
                id=func_id,
                kind="function",
                sig=f"function {func_name}({params_str.strip()})" + (f": {ret_type}" if ret_type else ""),
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(
                    params=parsed_params,
                    returns=ret_type,
                    raises=raises_list,
                    complexity=complexity_score,
                    calls=len(func_calls),
                    reads=http_reads,
                ),
                story=NodeStory(text=func_doc, source="deterministic", confidence="high"),
                snippet=raw_func_code if len(raw_func_code) <= 1500 else raw_func_code[:1500] + "...",
                content_hash=hash_content(raw_func_code),
            )
            nodes.append(func_card)

            edges.append(
                Edge(
                    src=file_id,
                    dst=func_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_function",
                    ),
                )
            )

            for callee, call_line in func_calls:
                edges.append(
                    Edge(
                        src=func_id,
                        dst=callee,
                        type=EdgeType.CALLS,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=norm_path,
                            start_line=call_line,
                            end_line=call_line,
                            how_derived="ts_call",
                        ),
                    )
                )

        # -------------------------------------------------------------------
        # 5. Arrow Functions & Variable Assigned Functions
        # -------------------------------------------------------------------
        for m in ARROW_FUNC_RE.finditer(sanitized):
            func_name = m.group(1)
            params_str = m.group(2) if m.group(2) is not None else (m.group(3) or "")
            ret_type = m.group(4).strip() if m.group(4) else None
            has_brace = m.group(5) == "{"

            start_line = _get_line_number(line_starts, m.start())

            if has_brace:
                open_brace_idx = m.end() - 1
                close_brace_idx = _find_matching_brace(sanitized, open_brace_idx)
                end_line = _get_line_number(line_starts, close_brace_idx)
                raw_func_code = source[m.start() : close_brace_idx + 1]
                func_body = source[open_brace_idx + 1 : close_brace_idx]
                body_offset = open_brace_idx + 1
            else:
                next_semi = sanitized.find(";", m.end())
                next_nl = sanitized.find("\n", m.end())
                if next_semi != -1 and (next_nl == -1 or next_semi < next_nl):
                    end_idx = next_semi
                elif next_nl != -1:
                    end_idx = next_nl
                else:
                    end_idx = len(sanitized)
                end_line = _get_line_number(line_starts, end_idx)
                raw_func_code = source[m.start() : end_idx]
                func_body = source[m.end() : end_idx]
                body_offset = m.end()

            func_id = NodeCard.make_id(lang_code, norm_path, func_name)
            func_doc = jsdoc_map.get(start_line, f"Arrow function {func_name}")

            parsed_params = _parse_params(params_str)
            raises_list = list(dict.fromkeys(THROW_RE.findall(func_body)))
            complexity_score = 1 + len(COMPLEXITY_RE.findall(func_body))

            func_calls = _extract_calls_from_code(
                func_body,
                line_starts,
                body_offset,
                norm_path,
            )

            http_reads = _extract_http_calls(func_body)

            func_card = NodeCard(
                id=func_id,
                kind="function",
                sig=f"const {func_name} = ({params_str.strip()})" + (f": {ret_type}" if ret_type else "") + " => ...",
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(
                    params=parsed_params,
                    returns=ret_type,
                    raises=raises_list,
                    complexity=complexity_score,
                    calls=len(func_calls),
                    reads=http_reads,
                ),
                story=NodeStory(text=func_doc, source="deterministic", confidence="high"),
                snippet=raw_func_code if len(raw_func_code) <= 1500 else raw_func_code[:1500] + "...",
                content_hash=hash_content(raw_func_code),
            )
            nodes.append(func_card)

            edges.append(
                Edge(
                    src=file_id,
                    dst=func_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_arrow_function",
                    ),
                )
            )

            for callee, call_line in func_calls:
                edges.append(
                    Edge(
                        src=func_id,
                        dst=callee,
                        type=EdgeType.CALLS,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=norm_path,
                            start_line=call_line,
                            end_line=call_line,
                            how_derived="ts_call",
                        ),
                    )
                )

        for m in FUNC_EXPR_RE.finditer(sanitized):
            func_name = m.group(1)
            params_str = m.group(2)
            ret_type = m.group(3).strip() if m.group(3) else None

            open_brace_idx = m.end() - 1
            close_brace_idx = _find_matching_brace(sanitized, open_brace_idx)

            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, close_brace_idx)
            func_id = NodeCard.make_id(lang_code, norm_path, func_name)
            func_doc = jsdoc_map.get(start_line, f"Function expression {func_name}")

            raw_func_code = source[m.start() : close_brace_idx + 1]
            func_body = source[open_brace_idx + 1 : close_brace_idx]

            parsed_params = _parse_params(params_str)
            raises_list = list(dict.fromkeys(THROW_RE.findall(func_body)))
            complexity_score = 1 + len(COMPLEXITY_RE.findall(func_body))

            func_calls = _extract_calls_from_code(
                func_body,
                line_starts,
                open_brace_idx + 1,
                norm_path,
            )

            http_reads = _extract_http_calls(func_body)

            func_card = NodeCard(
                id=func_id,
                kind="function",
                sig=f"const {func_name} = function({params_str.strip()})" + (f": {ret_type}" if ret_type else ""),
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(
                    params=parsed_params,
                    returns=ret_type,
                    raises=raises_list,
                    complexity=complexity_score,
                    calls=len(func_calls),
                    reads=http_reads,
                ),
                story=NodeStory(text=func_doc, source="deterministic", confidence="high"),
                snippet=raw_func_code if len(raw_func_code) <= 1500 else raw_func_code[:1500] + "...",
                content_hash=hash_content(raw_func_code),
            )
            nodes.append(func_card)

            edges.append(
                Edge(
                    src=file_id,
                    dst=func_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(
                        file=norm_path,
                        start_line=start_line,
                        end_line=end_line,
                        how_derived="ts_func_expr",
                    ),
                )
            )

            for callee, call_line in func_calls:
                edges.append(
                    Edge(
                        src=func_id,
                        dst=callee,
                        type=EdgeType.CALLS,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=norm_path,
                            start_line=call_line,
                            end_line=call_line,
                            how_derived="ts_call",
                        ),
                    )
                )

        # -------------------------------------------------------------------
        # 6. Hook / HOC-wrapped arrow functions (useCallback/useMemo/memo/forwardRef)
        # -------------------------------------------------------------------
        existing_ids = {n.id for n in nodes}
        for m in WRAPPED_ARROW_RE.finditer(sanitized):
            func_name = m.group(1)
            func_id = NodeCard.make_id(lang_code, norm_path, func_name)
            if func_id in existing_ids:
                continue
            params_str = m.group(2) if m.group(2) is not None else (m.group(3) or "")

            open_brace_idx = m.end() - 1
            close_brace_idx = _find_matching_brace(sanitized, open_brace_idx)
            start_line = _get_line_number(line_starts, m.start())
            end_line = _get_line_number(line_starts, close_brace_idx)

            raw_func_code = source[m.start() : close_brace_idx + 1]
            func_body = source[open_brace_idx + 1 : close_brace_idx]

            parsed_params = _parse_params(params_str)
            raises_list = list(dict.fromkeys(THROW_RE.findall(func_body)))
            complexity_score = 1 + len(COMPLEXITY_RE.findall(func_body))
            func_calls = _extract_calls_from_code(func_body, line_starts, open_brace_idx + 1, norm_path)
            http_reads = _extract_http_calls(func_body)

            func_card = NodeCard(
                id=func_id,
                kind="function",
                sig=f"const {func_name} = ({params_str.strip()}) => ...",
                span=Span(file=norm_path, start=start_line, end=end_line),
                facts=NodeFacts(
                    params=parsed_params,
                    raises=raises_list,
                    complexity=complexity_score,
                    calls=len(func_calls),
                    reads=http_reads,
                ),
                story=NodeStory(
                    text=jsdoc_map.get(start_line, f"Arrow function {func_name}"),
                    source="deterministic",
                    confidence="high",
                ),
                snippet=raw_func_code if len(raw_func_code) <= 1500 else raw_func_code[:1500] + "...",
                content_hash=hash_content(raw_func_code),
            )
            nodes.append(func_card)
            existing_ids.add(func_id)
            edges.append(
                Edge(
                    src=file_id,
                    dst=func_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(file=norm_path, start_line=start_line, end_line=end_line, how_derived="ts_hook_arrow"),
                )
            )
            for callee, call_line in func_calls:
                edges.append(
                    Edge(
                        src=func_id,
                        dst=callee,
                        type=EdgeType.CALLS,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(file=norm_path, start_line=call_line, end_line=call_line, how_derived="ts_call"),
                    )
                )

        # -------------------------------------------------------------------
        # 7. Module-level SCREAMING_SNAKE constants (API_BASE_URL, REMEMBER_ME_DAYS, …)
        # -------------------------------------------------------------------
        for m in CONST_DECL_RE.finditer(sanitized):
            const_name = m.group(1)
            const_id = NodeCard.make_id(lang_code, norm_path, const_name)
            if const_id in existing_ids:
                continue
            value_expr = m.group(2) or ""
            # Skip function-valued constants: those are captured as function nodes above.
            if "=>" in value_expr or value_expr.lstrip().startswith("function"):
                continue
            start_line = _get_line_number(line_starts, m.start())
            const_card = NodeCard(
                id=const_id,
                kind="variable",
                sig=f"const {const_name}",
                span=Span(file=norm_path, start=start_line, end=start_line),
                facts=NodeFacts(),
                story=NodeStory(
                    text=jsdoc_map.get(start_line, f"Module constant {const_name}"),
                    source="deterministic",
                    confidence="high",
                ),
                content_hash=hash_content(f"{const_name}={value_expr.strip()}"),
            )
            nodes.append(const_card)
            existing_ids.add(const_id)
            edges.append(
                Edge(
                    src=file_id,
                    dst=const_id,
                    type=EdgeType.DEFINED_IN,
                    confidence=Confidence.RESOLVED,
                    evidence=Evidence(file=norm_path, start_line=start_line, end_line=start_line, how_derived="ts_const"),
                )
            )

        _propagate_http_wrapper_calls(nodes, source)

        return ParseResult(
            file_path=Path(rel_path),
            rel_path=norm_path,
            language=lang_name,
            nodes=nodes,
            edges=edges,
            errors=errors,
        )
