"""Universal polyglot tree-sitter parser engine for 36+ programming languages.

Provides LanguageConfig dataclass for declarative language definitions and
PolyglotTreeSitterParser that dispatches to tree-sitter when grammars are
installed, with resilient regex fallback when they are not.
"""

from __future__ import annotations

import hashlib
import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

from repopeek.models.schema import Confidence, Edge, EdgeType, Evidence, NodeCard, NodeFacts, Span
from repopeek.parsers.base import BaseParser, ParseResult


# ---------------------------------------------------------------------------
# LanguageConfig: declarative tree-sitter language definition
# ---------------------------------------------------------------------------

@dataclass
class LanguageConfig:
    """Declarative configuration for a tree-sitter language grammar."""

    # Identity
    name: str                                           # human label, e.g. "go"
    ts_module: str                                      # Python module, e.g. "tree_sitter_go"
    ts_language_fn: str = "language"                    # attribute name returning the Language capsule

    # AST node type sets for classification
    class_types: FrozenSet[str] = field(default_factory=frozenset)
    function_types: FrozenSet[str] = field(default_factory=frozenset)
    import_types: FrozenSet[str] = field(default_factory=frozenset)
    call_types: FrozenSet[str] = field(default_factory=frozenset)

    # Name extraction
    name_field: str = "name"
    name_fallback_child_types: Tuple[str, ...] = ()

    # Body detection
    body_field: str = "body"
    body_fallback_child_types: Tuple[str, ...] = ()

    # Call name extraction
    call_function_field: str = "function"
    call_accessor_node_types: FrozenSet[str] = field(default_factory=frozenset)
    call_accessor_field: str = "attribute"

    # Supplementary extraction patterns (regex fallback)
    class_regex: str = ""
    function_regex: str = ""
    import_regex: str = ""

    # File extensions this config handles (for registry lookup)
    extensions: FrozenSet[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Language configurations for all supported languages
# ---------------------------------------------------------------------------

GO_CONFIG = LanguageConfig(
    name="go",
    ts_module="tree_sitter_go",
    class_types=frozenset({"type_declaration", "struct_type", "interface_type"}),
    function_types=frozenset({"function_declaration", "method_declaration"}),
    import_types=frozenset({"import_declaration", "import_spec"}),
    call_types=frozenset({"call_expression"}),
    call_accessor_node_types=frozenset({"selector_expression"}),
    call_accessor_field="field",
    class_regex=r'^\s*type\s+(\w+)\s+(?:struct|interface)\s*\{',
    function_regex=r'^\s*func\s+(?:\(\s*\w+\s+\*?\w+\)\s+)?(\w+)\s*\(',
    import_regex=r'^\s*(?:import\s+)?"([^"]+)"',
    extensions=frozenset({".go"}),
)

RUST_CONFIG = LanguageConfig(
    name="rust",
    ts_module="tree_sitter_rust",
    class_types=frozenset({"struct_item", "enum_item", "trait_item", "impl_item", "type_item"}),
    function_types=frozenset({"function_item", "associated_type"}),
    import_types=frozenset({"use_declaration"}),
    call_types=frozenset({"call_expression", "macro_invocation"}),
    call_accessor_node_types=frozenset({"field_expression", "scoped_identifier"}),
    class_regex=r'^\s*(?:pub\s+)?(?:struct|enum|trait|impl)\s+(\w+)',
    function_regex=r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)',
    import_regex=r'^\s*use\s+([\w:]+)',
    extensions=frozenset({".rs"}),
)

JAVA_CONFIG = LanguageConfig(
    name="java",
    ts_module="tree_sitter_java",
    class_types=frozenset({"class_declaration", "interface_declaration", "enum_declaration",
                           "annotation_type_declaration", "record_declaration"}),
    function_types=frozenset({"method_declaration", "constructor_declaration"}),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"method_invocation", "object_creation_expression"}),
    call_accessor_node_types=frozenset({"method_invocation"}),
    class_regex=r'^\s*(?:public|private|protected)?\s*(?:abstract|final|static)?\s*(?:class|interface|enum|record)\s+(\w+)',
    function_regex=r'^\s*(?:public|private|protected)?\s*(?:static|abstract|final|synchronized)?\s*\w[\w<>\[\],\s]*\s+(\w+)\s*\(',
    import_regex=r'^\s*import\s+(?:static\s+)?([\w.]+)',
    extensions=frozenset({".java"}),
)

C_CONFIG = LanguageConfig(
    name="c",
    ts_module="tree_sitter_c",
    class_types=frozenset({"struct_specifier", "enum_specifier", "union_specifier", "type_definition"}),
    function_types=frozenset({"function_definition"}),
    import_types=frozenset({"preproc_include"}),
    call_types=frozenset({"call_expression"}),
    name_field="declarator",
    body_field="body",
    body_fallback_child_types=("compound_statement",),
    class_regex=r'^\s*(?:typedef\s+)?(?:struct|enum|union)\s+(\w+)',
    function_regex=r'^\s*(?:\w[\w\s\*]*)\s+(\w+)\s*\([^)]*\)\s*\{',
    import_regex=r'^\s*#include\s+[<"]([^>"]+)[>"]',
    extensions=frozenset({".c", ".h"}),
)

CPP_CONFIG = LanguageConfig(
    name="cpp",
    ts_module="tree_sitter_cpp",
    class_types=frozenset({"class_specifier", "struct_specifier", "enum_specifier",
                           "union_specifier", "type_definition", "namespace_definition"}),
    function_types=frozenset({"function_definition", "template_declaration"}),
    import_types=frozenset({"preproc_include", "using_declaration"}),
    call_types=frozenset({"call_expression"}),
    call_accessor_node_types=frozenset({"field_expression", "qualified_identifier"}),
    name_field="declarator",
    body_fallback_child_types=("compound_statement", "declaration_list"),
    class_regex=r'^\s*(?:class|struct|namespace)\s+(\w+)',
    function_regex=r'^\s*(?:[\w\s\*&:~<>]+)\s+(\w+)\s*\([^)]*\)\s*(?:const|override|final)?\s*\{',
    import_regex=r'^\s*#include\s+[<"]([^>"]+)[>"]',
    extensions=frozenset({".cpp", ".cc", ".cxx", ".hpp", ".cu", ".cuh"}),
)

CSHARP_CONFIG = LanguageConfig(
    name="csharp",
    ts_module="tree_sitter_c_sharp",
    ts_language_fn="language",
    class_types=frozenset({"class_declaration", "interface_declaration", "struct_declaration",
                           "enum_declaration", "record_declaration", "namespace_declaration"}),
    function_types=frozenset({"method_declaration", "constructor_declaration", "property_declaration"}),
    import_types=frozenset({"using_directive"}),
    call_types=frozenset({"invocation_expression", "object_creation_expression"}),
    call_accessor_node_types=frozenset({"member_access_expression"}),
    class_regex=r'^\s*(?:public|private|protected|internal)?\s*(?:abstract|sealed|static|partial)?\s*(?:class|interface|struct|enum|record|namespace)\s+(\w+)',
    function_regex=r'^\s*(?:public|private|protected|internal)?\s*(?:static|virtual|override|abstract|async)?\s*\w[\w<>\[\],\s]*\s+(\w+)\s*[(<]',
    import_regex=r'^\s*using\s+([\w.]+)',
    extensions=frozenset({".cs"}),
)

RUBY_CONFIG = LanguageConfig(
    name="ruby",
    ts_module="tree_sitter_ruby",
    class_types=frozenset({"class", "module", "singleton_class"}),
    function_types=frozenset({"method", "singleton_method"}),
    import_types=frozenset({"call"}),  # require/require_relative
    call_types=frozenset({"call", "method_call"}),
    call_accessor_node_types=frozenset({"call"}),
    class_regex=r'^\s*(?:class|module)\s+(\w[\w:]*)',
    function_regex=r'^\s*def\s+(?:self\.)?(\w+[?!=]?)',
    import_regex=r'^\s*(?:require|require_relative|load)\s+[\'"]([^\'"]+)[\'"]',
    extensions=frozenset({".rb", ".rake"}),
)

PHP_CONFIG = LanguageConfig(
    name="php",
    ts_module="tree_sitter_php",
    class_types=frozenset({"class_declaration", "interface_declaration", "trait_declaration",
                           "enum_declaration", "namespace_definition"}),
    function_types=frozenset({"function_definition", "method_declaration"}),
    import_types=frozenset({"namespace_use_declaration"}),
    call_types=frozenset({"function_call_expression", "method_call_expression",
                          "member_call_expression", "scoped_call_expression"}),
    class_regex=r'^\s*(?:abstract|final)?\s*(?:class|interface|trait|enum)\s+(\w+)',
    function_regex=r'^\s*(?:public|private|protected)?\s*(?:static)?\s*function\s+(\w+)',
    import_regex=r'^\s*(?:use|namespace)\s+([\w\\]+)',
    extensions=frozenset({".php"}),
)

KOTLIN_CONFIG = LanguageConfig(
    name="kotlin",
    ts_module="tree_sitter_kotlin",
    class_types=frozenset({"class_declaration", "interface_declaration", "object_declaration",
                           "enum_class_body"}),
    function_types=frozenset({"function_declaration"}),
    import_types=frozenset({"import_header"}),
    call_types=frozenset({"call_expression"}),
    call_accessor_node_types=frozenset({"navigation_expression"}),
    class_regex=r'^\s*(?:data|sealed|abstract|open|inner|enum)?\s*class\s+(\w+)',
    function_regex=r'^\s*(?:override|open|internal|private|protected|public)?\s*(?:suspend\s+)?fun\s+(\w+)',
    import_regex=r'^\s*import\s+([\w.]+)',
    extensions=frozenset({".kt", ".kts"}),
)

SCALA_CONFIG = LanguageConfig(
    name="scala",
    ts_module="tree_sitter_scala",
    class_types=frozenset({"class_definition", "trait_definition", "object_definition",
                           "enum_definition"}),
    function_types=frozenset({"function_definition", "val_definition", "var_definition"}),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"call_expression"}),
    class_regex=r'^\s*(?:case\s+)?(?:class|trait|object)\s+(\w+)',
    function_regex=r'^\s*(?:override\s+)?def\s+(\w+)',
    import_regex=r'^\s*import\s+([\w.]+)',
    extensions=frozenset({".scala"}),
)

SWIFT_CONFIG = LanguageConfig(
    name="swift",
    ts_module="tree_sitter_swift",
    class_types=frozenset({"class_declaration", "struct_declaration", "protocol_declaration",
                           "enum_declaration", "extension_declaration"}),
    function_types=frozenset({"function_declaration", "init_declaration", "subscript_declaration"}),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"call_expression"}),
    call_accessor_node_types=frozenset({"member_expression"}),
    class_regex=r'^\s*(?:public|private|internal|open|fileprivate)?\s*(?:final\s+)?(?:class|struct|protocol|enum|extension)\s+(\w+)',
    function_regex=r'^\s*(?:public|private|internal|open|fileprivate)?\s*(?:static|class|override|mutating)?\s*func\s+(\w+)',
    import_regex=r'^\s*import\s+(\w+)',
    extensions=frozenset({".swift"}),
)

LUA_CONFIG = LanguageConfig(
    name="lua",
    ts_module="tree_sitter_lua",
    class_types=frozenset(),
    function_types=frozenset({"function_declaration", "function_definition_statement",
                              "local_function_definition_statement"}),
    import_types=frozenset({"function_call"}),  # require()
    call_types=frozenset({"function_call"}),
    function_regex=r'^\s*(?:local\s+)?function\s+([.\w:]+)',
    import_regex=r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    extensions=frozenset({".lua", ".luau"}),
)

ZIG_CONFIG = LanguageConfig(
    name="zig",
    ts_module="tree_sitter_zig",
    class_types=frozenset({"container_declaration"}),
    function_types=frozenset({"fn_proto"}),
    import_types=frozenset(),
    call_types=frozenset({"call_expr", "builtin_call_expr"}),
    function_regex=r'^\s*(?:pub\s+)?fn\s+(\w+)',
    import_regex=r'@import\s*\(\s*"([^"]+)"\s*\)',
    extensions=frozenset({".zig"}),
)

POWERSHELL_CONFIG = LanguageConfig(
    name="powershell",
    ts_module="tree_sitter_powershell",
    class_types=frozenset({"class_statement", "enum_statement"}),
    function_types=frozenset({"function_statement"}),
    import_types=frozenset({"using_statement"}),
    call_types=frozenset({"command", "command_expression"}),
    class_regex=r'^\s*class\s+(\w+)',
    function_regex=r'^\s*function\s+([\w-]+)',
    import_regex=r'^\s*(?:Import-Module|using\s+module)\s+([\w.-]+)',
    extensions=frozenset({".ps1", ".psm1", ".psd1"}),
)

ELIXIR_CONFIG = LanguageConfig(
    name="elixir",
    ts_module="tree_sitter_elixir",
    class_types=frozenset({"call"}),  # defmodule
    function_types=frozenset({"call"}),  # def/defp
    import_types=frozenset({"call"}),  # import/alias/use/require
    call_types=frozenset({"call", "dot"}),
    class_regex=r'^\s*defmodule\s+([\w.]+)',
    function_regex=r'^\s*(?:def|defp)\s+(\w+)',
    import_regex=r'^\s*(?:import|alias|use|require)\s+([\w.]+)',
    extensions=frozenset({".ex", ".exs"}),
)

ERLANG_CONFIG = LanguageConfig(
    name="erlang",
    ts_module="tree_sitter_erlang",
    class_types=frozenset(),
    function_types=frozenset({"function_clause"}),
    import_types=frozenset(),
    call_types=frozenset({"call"}),
    function_regex=r'^(\w+)\s*\([^)]*\)\s*(?:when\b|->)',
    import_regex=r'-(?:import|include|include_lib)\s*\(\s*(?:\'([^\']+)\'|"([^"]+)")',
    extensions=frozenset({".erl", ".hrl"}),
)

FORTRAN_CONFIG = LanguageConfig(
    name="fortran",
    ts_module="tree_sitter_fortran",
    class_types=frozenset({"module", "derived_type_definition"}),
    function_types=frozenset({"function", "subroutine", "program"}),
    import_types=frozenset({"use_statement"}),
    call_types=frozenset({"call_expression", "function_reference"}),
    class_regex=r'^\s*(?:module|type)\s+(\w+)',
    function_regex=r'^\s*(?:recursive\s+)?(?:pure\s+)?(?:elemental\s+)?(?:function|subroutine|program)\s+(\w+)',
    import_regex=r'^\s*use\s+(\w+)',
    extensions=frozenset({".f", ".f90", ".f95", ".f03", ".f08"}),
)

JULIA_CONFIG = LanguageConfig(
    name="julia",
    ts_module="tree_sitter_julia",
    class_types=frozenset({"struct_definition", "abstract_definition", "module_definition"}),
    function_types=frozenset({"function_definition", "short_function_definition", "macro_definition"}),
    import_types=frozenset({"import_statement", "using_statement"}),
    call_types=frozenset({"call_expression", "macro_expression"}),
    class_regex=r'^\s*(?:mutable\s+)?struct\s+(\w+)',
    function_regex=r'^\s*function\s+(\w+)',
    import_regex=r'^\s*(?:using|import)\s+([\w.]+)',
    extensions=frozenset({".jl"}),
)

OBJC_CONFIG = LanguageConfig(
    name="objc",
    ts_module="tree_sitter_objc",
    class_types=frozenset({"class_interface", "class_implementation", "protocol_declaration",
                           "category_interface", "category_implementation"}),
    function_types=frozenset({"method_declaration", "function_definition"}),
    import_types=frozenset({"preproc_import", "preproc_include"}),
    call_types=frozenset({"message_expression", "call_expression"}),
    class_regex=r'^\s*@(?:interface|implementation|protocol)\s+(\w+)',
    function_regex=r'^\s*[+-]\s*\([^)]*\)\s*(\w+)',
    import_regex=r'^\s*#(?:import|include)\s+[<"]([^>"]+)[>"]',
    extensions=frozenset({".m", ".mm"}),
)

VERILOG_CONFIG = LanguageConfig(
    name="verilog",
    ts_module="tree_sitter_verilog",
    class_types=frozenset({"module_declaration", "interface_declaration"}),
    function_types=frozenset({"task_declaration", "function_declaration"}),
    import_types=frozenset({"module_instantiation"}),
    call_types=frozenset({"module_instantiation", "system_tf_call"}),
    class_regex=r'^\s*module\s+(\w+)',
    function_regex=r'^\s*(?:task|function)\s+(?:\w+\s+)?(\w+)',
    import_regex=r'`include\s+"([^"]+)"',
    extensions=frozenset({".v", ".sv", ".svh"}),
)

DART_CONFIG = LanguageConfig(
    name="dart",
    ts_module="tree_sitter_dart",
    class_types=frozenset({"class_definition", "mixin_declaration", "enum_declaration",
                           "extension_declaration"}),
    function_types=frozenset({"function_signature", "method_signature", "function_body"}),
    import_types=frozenset({"import_or_export"}),
    call_types=frozenset({"function_expression_body", "identifier"}),
    class_regex=r'^\s*(?:abstract\s+)?class\s+(\w+)',
    function_regex=r'^\s*(?:\w[\w<>]*\s+)?(\w+)\s*\([^)]*\)\s*(?:async\s*)?\{',
    import_regex=r"^\s*import\s+'([^']+)'",
    extensions=frozenset({".dart"}),
)

TERRAFORM_CONFIG = LanguageConfig(
    name="terraform",
    ts_module="tree_sitter_hcl",
    class_types=frozenset({"block"}),
    function_types=frozenset(),
    import_types=frozenset(),
    call_types=frozenset({"function_call"}),
    class_regex=r'^\s*(?:resource|data|module|variable|output|provider|locals|terraform)\s+"?(\w+)"?\s+"?(\w+)"?',
    function_regex=r'',
    import_regex=r'^\s*source\s*=\s*"([^"]+)"',
    extensions=frozenset({".tf", ".tfvars", ".hcl"}),
)

SOLIDITY_CONFIG = LanguageConfig(
    name="solidity",
    ts_module="tree_sitter_solidity",
    class_types=frozenset({"contract_declaration", "interface_declaration", "library_declaration",
                           "struct_declaration", "enum_declaration"}),
    function_types=frozenset({"function_definition", "constructor_definition", "modifier_definition"}),
    import_types=frozenset({"import_directive"}),
    call_types=frozenset({"call_expression"}),
    class_regex=r'^\s*(?:abstract\s+)?(?:contract|interface|library)\s+(\w+)',
    function_regex=r'^\s*function\s+(\w+)',
    import_regex=r'^\s*import\s+(?:\{[^}]*\}\s+from\s+)?[\'"]([^\'"]+)[\'"]',
    extensions=frozenset({".sol"}),
)

GROOVY_CONFIG = LanguageConfig(
    name="groovy",
    ts_module="tree_sitter_groovy",
    class_types=frozenset({"class_definition"}),
    function_types=frozenset({"method_definition", "function_definition"}),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"call_expression", "method_call_expression"}),
    class_regex=r'^\s*(?:public|private|protected)?\s*class\s+(\w+)',
    function_regex=r'^\s*(?:def|void|public|private|protected|static)\s+(\w+)\s*\(',
    import_regex=r'^\s*import\s+([\w.]+)',
    extensions=frozenset({".groovy", ".gradle"}),
)

MARKDOWN_CONFIG = LanguageConfig(
    name="markdown",
    ts_module="",  # no tree-sitter, regex only
    class_types=frozenset(),
    function_types=frozenset(),
    import_types=frozenset(),
    call_types=frozenset(),
    class_regex=r'^#{1,3}\s+(.+)',  # headings as sections
    function_regex=r'',
    import_regex=r'\[([^\]]+)\]\(([^)]+)\)',  # markdown links
    extensions=frozenset({".md", ".mdx"}),
)


# ---------------------------------------------------------------------------
# Registry: map FileType -> LanguageConfig
# ---------------------------------------------------------------------------

LANGUAGE_CONFIGS: Dict[str, LanguageConfig] = {
    "go": GO_CONFIG,
    "rust": RUST_CONFIG,
    "java": JAVA_CONFIG,
    "c": C_CONFIG,
    "cpp": CPP_CONFIG,
    "csharp": CSHARP_CONFIG,
    "ruby": RUBY_CONFIG,
    "php": PHP_CONFIG,
    "kotlin": KOTLIN_CONFIG,
    "scala": SCALA_CONFIG,
    "swift": SWIFT_CONFIG,
    "lua": LUA_CONFIG,
    "zig": ZIG_CONFIG,
    "powershell": POWERSHELL_CONFIG,
    "elixir": ELIXIR_CONFIG,
    "erlang": ERLANG_CONFIG,
    "fortran": FORTRAN_CONFIG,
    "julia": JULIA_CONFIG,
    "objc": OBJC_CONFIG,
    "verilog": VERILOG_CONFIG,
    "dart": DART_CONFIG,
    "terraform": TERRAFORM_CONFIG,
    "solidity": SOLIDITY_CONFIG,
    "groovy": GROOVY_CONFIG,
    "markdown": MARKDOWN_CONFIG,
}


# ---------------------------------------------------------------------------
# PolyglotTreeSitterParser
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _make_id(lang: str, rel_path: str, qualified_name: str) -> str:
    norm_path = Path(rel_path).as_posix().lstrip("./")
    return f"{lang}:{norm_path}::{qualified_name}"


class PolyglotTreeSitterParser(BaseParser):
    """Universal code parser that handles 25+ languages via tree-sitter AST
    parsing with transparent regex fallback when grammars are unavailable."""

    def __init__(self, config: LanguageConfig) -> None:
        self.config = config
        self._ts_available: Optional[bool] = None

    def _check_ts(self) -> bool:
        """Lazily check if tree-sitter and the language grammar are importable."""
        if self._ts_available is not None:
            return self._ts_available
        if not self.config.ts_module:
            self._ts_available = False
            return False
        try:
            importlib.import_module("tree_sitter")
            importlib.import_module(self.config.ts_module)
            self._ts_available = True
        except ImportError:
            self._ts_available = False
        return self._ts_available

    def parse_source(
        self,
        source: str,
        rel_path: str,
        repo_root: Optional[Path] = None,
    ) -> ParseResult:
        """Parse source code into nodes and edges, using tree-sitter or regex fallback."""
        if self._check_ts():
            return self._parse_with_tree_sitter(source, rel_path)
        return self._parse_with_regex(source, rel_path)

    # ------------------------------------------------------------------
    # Tree-sitter extraction
    # ------------------------------------------------------------------

    def _parse_with_tree_sitter(self, source: str, rel_path: str) -> ParseResult:
        """Full AST extraction via tree-sitter."""
        lang = self.config.name
        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        errors: List[str] = []
        seen_ids: set = set()

        try:
            from tree_sitter import Language, Parser
            mod = importlib.import_module(self.config.ts_module)
            lang_fn = getattr(mod, self.config.ts_language_fn, None)
            if lang_fn is None:
                lang_fn = getattr(mod, "language", None)
            if lang_fn is None:
                return self._parse_with_regex(source, rel_path)
            language = Language(lang_fn())
            parser = Parser(language)
        except Exception as e:
            errors.append(f"tree-sitter init failed: {e}")
            return self._parse_with_regex(source, rel_path)

        source_bytes = source.encode("utf-8")
        if source_bytes and not source_bytes.endswith(b"\n"):
            source_bytes += b"\n"

        try:
            tree = parser.parse(source_bytes)
        except Exception as e:
            errors.append(f"tree-sitter parse error: {e}")
            return self._parse_with_regex(source, rel_path)

        # Add file node
        file_node_id = _make_id(lang, rel_path, Path(rel_path).stem)
        file_node = NodeCard(
            id=file_node_id,
            kind="file",
            sig=rel_path,
            span=Span(file=rel_path, start=1, end=max(1, source.count("\n") + 1)),
            facts=NodeFacts(),
            content_hash=_content_hash(source),
        )
        nodes.append(file_node)
        seen_ids.add(file_node_id)

        namespace_stack: List[str] = []

        def _node_text(node) -> str:
            return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        def _get_name(node) -> Optional[str]:
            name_child = node.child_by_field_name(self.config.name_field)
            if name_child:
                return _node_text(name_child).strip()
            for child in node.children:
                if child.type in self.config.name_fallback_child_types:
                    return _node_text(child).strip()
                if child.type == "identifier":
                    return _node_text(child).strip()
                if child.type == "name":
                    return _node_text(child).strip()
                if child.type == "type_identifier":
                    return _node_text(child).strip()
            return None

        def _walk(cursor_node):
            ntype = cursor_node.type

            # Class / struct / interface / module
            if ntype in self.config.class_types:
                name = _get_name(cursor_node)
                if name:
                    qualified = ".".join(namespace_stack + [name]) if namespace_stack else name
                    nid = _make_id(lang, rel_path, qualified)
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        start_line = cursor_node.start_point[0] + 1
                        end_line = cursor_node.end_point[0] + 1
                        nodes.append(NodeCard(
                            id=nid, kind="class", sig=name,
                            span=Span(file=rel_path, start=start_line, end=end_line),
                            facts=NodeFacts(), content_hash=_content_hash(_node_text(cursor_node)),
                        ))
                        edges.append(Edge(
                            src=nid, dst=file_node_id, type=EdgeType.DEFINED_IN,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(file=rel_path, start_line=start_line,
                                              end_line=end_line, how_derived="ast_class"),
                        ))
                    namespace_stack.append(name)
                    for child in cursor_node.children:
                        _walk(child)
                    namespace_stack.pop()
                    return

            # Function / method
            if ntype in self.config.function_types:
                name = _get_name(cursor_node)
                if name:
                    qualified = ".".join(namespace_stack + [name]) if namespace_stack else name
                    nid = _make_id(lang, rel_path, qualified)
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        start_line = cursor_node.start_point[0] + 1
                        end_line = cursor_node.end_point[0] + 1
                        nodes.append(NodeCard(
                            id=nid, kind="function", sig=f"{name}()",
                            span=Span(file=rel_path, start=start_line, end=end_line),
                            facts=NodeFacts(), content_hash=_content_hash(_node_text(cursor_node)),
                        ))
                        # DEFINED_IN file
                        edges.append(Edge(
                            src=nid, dst=file_node_id, type=EdgeType.DEFINED_IN,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(file=rel_path, start_line=start_line,
                                              end_line=end_line, how_derived="ast_function"),
                        ))
                        # DEFINED_IN enclosing class if nested
                        if namespace_stack:
                            parent_q = ".".join(namespace_stack)
                            parent_id = _make_id(lang, rel_path, parent_q)
                            if parent_id in seen_ids:
                                edges.append(Edge(
                                    src=nid, dst=parent_id, type=EdgeType.DEFINED_IN,
                                    confidence=Confidence.RESOLVED,
                                    evidence=Evidence(file=rel_path, start_line=start_line,
                                                      end_line=end_line, how_derived="ast_method"),
                                ))

            # Import
            if ntype in self.config.import_types:
                text = _node_text(cursor_node).strip()
                start_line = cursor_node.start_point[0] + 1
                edges.append(Edge(
                    src=file_node_id, dst=f"ext:{text}", type=EdgeType.IMPORTS,
                    confidence=Confidence.EXTERNAL,
                    evidence=Evidence(file=rel_path, start_line=start_line,
                                      end_line=start_line, how_derived="ast_import"),
                ))

            # Call
            if ntype in self.config.call_types:
                func_node = cursor_node.child_by_field_name(self.config.call_function_field)
                callee_name = None
                if func_node:
                    if func_node.type in self.config.call_accessor_node_types:
                        attr_node = func_node.child_by_field_name(self.config.call_accessor_field)
                        if attr_node:
                            callee_name = _node_text(attr_node).strip()
                        else:
                            callee_name = _node_text(func_node).strip()
                    else:
                        callee_name = _node_text(func_node).strip()
                if callee_name:
                    start_line = cursor_node.start_point[0] + 1
                    caller_id = file_node_id
                    if namespace_stack:
                        caller_id = _make_id(lang, rel_path, ".".join(namespace_stack))
                    edges.append(Edge(
                        src=caller_id, dst=f"unresolved:{callee_name}", type=EdgeType.CALLS,
                        confidence=Confidence.AMBIGUOUS,
                        evidence=Evidence(file=rel_path, start_line=start_line,
                                          end_line=start_line, how_derived="ast_call"),
                    ))

            # Recurse children
            for child in cursor_node.children:
                _walk(child)

        _walk(tree.root_node)

        return ParseResult(
            file_path=Path(rel_path),
            rel_path=rel_path,
            language=lang,
            nodes=nodes,
            edges=edges,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Regex fallback extraction
    # ------------------------------------------------------------------

    def _parse_with_regex(self, source: str, rel_path: str) -> ParseResult:
        """Resilient regex-based extraction when tree-sitter is unavailable."""
        lang = self.config.name
        nodes: List[NodeCard] = []
        edges: List[Edge] = []
        lines = source.splitlines()
        seen_ids: set = set()
        total_lines = len(lines)

        # File node
        file_node_id = _make_id(lang, rel_path, Path(rel_path).stem)
        nodes.append(NodeCard(
            id=file_node_id, kind="file", sig=rel_path,
            span=Span(file=rel_path, start=1, end=max(1, total_lines)),
            facts=NodeFacts(), content_hash=_content_hash(source),
        ))
        seen_ids.add(file_node_id)

        # Extract classes
        if self.config.class_regex:
            pat = re.compile(self.config.class_regex, re.MULTILINE)
            for i, line in enumerate(lines, 1):
                m = pat.match(line)
                if m:
                    name = m.group(1)
                    nid = _make_id(lang, rel_path, name)
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        nodes.append(NodeCard(
                            id=nid, kind="class", sig=name,
                            span=Span(file=rel_path, start=i, end=i),
                            facts=NodeFacts(), content_hash=_content_hash(line),
                        ))
                        edges.append(Edge(
                            src=nid, dst=file_node_id, type=EdgeType.DEFINED_IN,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(file=rel_path, start_line=i, end_line=i,
                                              how_derived="regex_class"),
                        ))

        # Extract functions
        if self.config.function_regex:
            pat = re.compile(self.config.function_regex, re.MULTILINE)
            for i, line in enumerate(lines, 1):
                m = pat.match(line)
                if m:
                    name = m.group(1)
                    nid = _make_id(lang, rel_path, name)
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        nodes.append(NodeCard(
                            id=nid, kind="function", sig=f"{name}()",
                            span=Span(file=rel_path, start=i, end=i),
                            facts=NodeFacts(), content_hash=_content_hash(line),
                        ))
                        edges.append(Edge(
                            src=nid, dst=file_node_id, type=EdgeType.DEFINED_IN,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(file=rel_path, start_line=i, end_line=i,
                                              how_derived="regex_function"),
                        ))

        # Extract imports
        if self.config.import_regex:
            pat = re.compile(self.config.import_regex, re.MULTILINE)
            for i, line in enumerate(lines, 1):
                for m in pat.finditer(line):
                    target = m.group(m.lastindex) if m.lastindex else m.group(1)
                    if target:
                        edges.append(Edge(
                            src=file_node_id, dst=f"ext:{target}", type=EdgeType.IMPORTS,
                            confidence=Confidence.EXTERNAL,
                            evidence=Evidence(file=rel_path, start_line=i, end_line=i,
                                              how_derived="regex_import"),
                        ))

        return ParseResult(
            file_path=Path(rel_path),
            rel_path=rel_path,
            language=lang,
            nodes=nodes,
            edges=edges,
        )
