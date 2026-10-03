"""Cross-file symbol and import resolver for RepoPeek canonical property graph."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from repopeek.models.schema import Confidence, Edge, EdgeType, NodeCard


class SymbolResolver:
    """Resolves cross-file imports, function calls, class inheritance, and script runs."""

    def __init__(self, nodes: List[NodeCard], edges: List[Edge]) -> None:
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges

        # Indexes for fast lookup
        self.file_nodes: Dict[str, str] = {}  # norm_rel_path -> file_node_id
        self.module_to_file: Dict[str, str] = {}  # dotted.module.path -> file_node_id
        self.symbols_by_qualname: Dict[Tuple[str, str], str] = {}  # (norm_rel_path, qualname) -> node_id
        self.symbols_by_name: Dict[str, List[str]] = {}  # bare_name -> [node_id, ...]
        self.tables_by_name: Dict[str, str] = {}  # table_name -> table_node_id
        self.file_imports: Dict[str, Dict[str, str]] = {}  # file_path -> {imported_name: full_target}

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Construct multi-level index maps from node cards and import edges."""
        for nid, card in self.nodes.items():
            if not card.span:
                continue
            fpath = card.span.file

            if card.kind in ("file", "module"):
                self.file_nodes[fpath] = nid
                # Convert path to dotted module notation (e.g. src/billing/invoice.py -> src.billing.invoice)
                dotted = fpath.replace("/", ".").replace("\\", ".")
                if dotted.endswith(".py"):
                    dotted = dotted[:-3]
                self.module_to_file[dotted] = nid
                # Also index suffix subpaths (e.g. tests.fixtures.sample_repo.src.billing.invoice)
                parts = dotted.split(".")
                for i in range(len(parts)):
                    suffix = ".".join(parts[i:])
                    if suffix not in self.module_to_file:
                        self.module_to_file[suffix] = nid

            elif card.kind == "sql_table":
                tname = card.facts.writes[0] if card.facts.writes else card.id.split("::table.")[-1]
                self.tables_by_name[tname.lower()] = nid

            # Index symbol names (classes, functions, methods)
            if "::" in nid:
                qualname = nid.split("::")[-1]
                self.symbols_by_qualname[(fpath, qualname)] = nid
                bare_name = qualname.split(".")[-1]
                self.symbols_by_name.setdefault(bare_name, []).append(nid)

        # Index IMPORTS edges per file
        for edge in self.edges:
            if edge.type == EdgeType.IMPORTS:
                src_card = self.nodes.get(edge.src)
                if src_card and src_card.span:
                    fpath = src_card.span.file
                    self.file_imports.setdefault(fpath, {})
                    imported_name = edge.dst.split(".")[-1]
                    self.file_imports[fpath][imported_name] = edge.dst
                    self.file_imports[fpath][edge.dst] = edge.dst

    def resolve(self) -> List[Edge]:
        """Resolve all edge destinations to concrete canonical node IDs where possible."""
        resolved_edges: List[Edge] = []

        for edge in self.edges:
            new_edge = edge.model_copy()
            src_card = self.nodes.get(new_edge.src)
            src_file = src_card.span.file if src_card and src_card.span else ""

            # Already resolved to a valid existing node ID
            if new_edge.dst in self.nodes:
                resolved_edges.append(new_edge)
                continue

            # Resolve based on edge relationship type
            if new_edge.type in (EdgeType.CALLS, EdgeType.INHERITS):
                target_id, conf = self._resolve_symbol(src_file, new_edge.dst)
                if target_id:
                    new_edge.dst = target_id
                    new_edge.confidence = conf
                else:
                    new_edge.confidence = Confidence.EXTERNAL

            elif new_edge.type == EdgeType.IMPORTS:
                target_id = self._resolve_import(src_file, new_edge.dst)
                if target_id:
                    new_edge.dst = target_id
                    new_edge.confidence = Confidence.RESOLVED
                else:
                    new_edge.confidence = Confidence.EXTERNAL

            elif new_edge.type == EdgeType.RUNS_SCRIPT:
                target_id = self._resolve_script_path(new_edge.dst)
                if target_id:
                    new_edge.dst = target_id
                    new_edge.confidence = Confidence.RESOLVED
                else:
                    new_edge.confidence = Confidence.UNRESOLVED

            elif new_edge.type in (EdgeType.READS, EdgeType.WRITES):
                # Check if target is a known SQL table
                t_lower = new_edge.dst.lower()
                if t_lower in self.tables_by_name:
                    new_edge.dst = self.tables_by_name[t_lower]
                    new_edge.confidence = Confidence.RESOLVED

            resolved_edges.append(new_edge)

        return resolved_edges

    def _resolve_symbol(self, src_file: str, callee_name: str) -> Tuple[Optional[str], Confidence]:
        """Resolve a function or class reference across local file, imports, or global symbols."""
        bare_name = callee_name.split(".")[-1]

        # 1. Local scope inside same file
        if (src_file, callee_name) in self.symbols_by_qualname:
            return self.symbols_by_qualname[(src_file, callee_name)], Confidence.RESOLVED
        if (src_file, bare_name) in self.symbols_by_qualname:
            return self.symbols_by_qualname[(src_file, bare_name)], Confidence.RESOLVED

        # 2. Check if imported in this file
        imports = self.file_imports.get(src_file, {})
        if bare_name in imports:
            import_target = imports[bare_name]
            resolved = self._find_node_by_dotted_path(import_target)
            if resolved:
                return resolved, Confidence.RESOLVED

        # 3. Global lookup across repository
        candidates = self.symbols_by_name.get(bare_name, [])
        if len(candidates) == 1:
            return candidates[0], Confidence.RESOLVED
        elif len(candidates) > 1:
            return candidates[0], Confidence.AMBIGUOUS

        return None, Confidence.EXTERNAL

    def _resolve_import(self, src_file: str, import_path: str) -> Optional[str]:
        """Resolve an import path to a concrete file or symbol node in the repository."""
        # Try direct dotted module match
        if import_path in self.module_to_file:
            return self.module_to_file[import_path]

        # Try stripping leading segments (e.g. tests.fixtures.sample_repo.src.billing.invoice)
        parts = import_path.split(".")
        for i in range(len(parts)):
            suffix = ".".join(parts[i:])
            if suffix in self.module_to_file:
                return self.module_to_file[suffix]

        # Try matching as symbol in a module (e.g. module.symbol)
        if "." in import_path:
            mod_part, sym_part = import_path.rsplit(".", 1)
            file_id = self._resolve_import(src_file, mod_part)
            if file_id:
                file_card = self.nodes.get(file_id)
                if file_card and file_card.span:
                    fpath = file_card.span.file
                    if (fpath, sym_part) in self.symbols_by_qualname:
                        return self.symbols_by_qualname[(fpath, sym_part)]

        return None

    def _resolve_script_path(self, script_path: str) -> Optional[str]:
        """Match a script path string (e.g. 'src/billing/invoice.py') to its file node."""
        norm = Path(script_path).as_posix().lstrip("./")
        if norm in self.file_nodes:
            return self.file_nodes[norm]

        # Match by suffix
        for fpath, nid in self.file_nodes.items():
            if fpath.endswith(norm) or norm.endswith(fpath):
                return nid
        return None

    def _find_node_by_dotted_path(self, dotted_path: str) -> Optional[str]:
        """Lookup node card by dotted path e.g. 'src.billing.validators.validate_invoice'."""
        if "." in dotted_path:
            mod_part, sym_part = dotted_path.rsplit(".", 1)
            for (fpath, qualname), nid in self.symbols_by_qualname.items():
                if qualname == sym_part and (mod_part in fpath.replace("/", ".")):
                    return nid
        return None
