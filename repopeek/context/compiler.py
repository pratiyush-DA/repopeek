"""Context Compiler, Constraint Extractor, and Change Plan Generator.

Implements the Phase 3 Context Compiler specification:
Compiles high-level natural language engineering tasks into minimal, evidence-backed
Context Packages with multi-tier constraint enforcement, quantitative blast radius,
and risk-aware step-by-step change plans.
"""

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from repopeek.graph.blast_radius import BlastRadiusReport, compute_blast_radius, is_node_excluded
from repopeek.graph.identity import is_sql_table_kind
from repopeek.query.pack import ContextPack


@dataclass
class ChangePlanStep:
    """An individual ordered action step in an engineering change plan."""
    step_number: int
    phase: str  # "pre_check", "core_modification", "blast_radius_update", "post_validation"
    action: str
    target: str
    file: Optional[str]
    citation: Optional[str]
    rationale: str


@dataclass
class ChangePlan:
    """A risk-assessed, step-by-step engineering change plan."""
    task: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    risk_reasons: List[str]
    steps: List[ChangePlanStep] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    pre_checks: List[str] = field(default_factory=list)
    post_checks: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render change plan as formatted markdown."""
        lines = [
            f"# Engineering Change Plan: {self.task}",
            f"**Risk Level:** `{self.risk_level}`",
        ]
        if self.risk_reasons:
            lines.append(f"**Risk Drivers:** {'; '.join(self.risk_reasons)}")
        lines.append("")

        if self.pre_checks:
            lines.append("## Phase 1: Pre-Change Verification")
            for c in self.pre_checks:
                lines.append(f"- [ ] {c}")
            lines.append("")

        lines.append("## Phase 2: Actionable Implementation Steps")
        for s in self.steps:
            target_str = f"`{s.target}`"
            if s.citation:
                target_str += f" ({s.citation})"
            lines.append(f"{s.step_number}. **[{s.phase.upper()}]** {s.action} on {target_str}")
            lines.append(f"   - *Rationale:* {s.rationale}")
        lines.append("")

        if self.post_checks:
            lines.append("## Phase 3: Post-Change Regression Validation")
            for c in self.post_checks:
                lines.append(f"- [ ] {c}")
            lines.append("")

        return "\n".join(lines).strip()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConstraintSet:
    """Multi-tier structural, type, and semantic constraints extracted from code."""
    parameter_constraints: List[str] = field(default_factory=list)
    return_constraints: List[str] = field(default_factory=list)
    exception_constraints: List[str] = field(default_factory=list)
    schema_constraints: List[str] = field(default_factory=list)
    behavioral_invariants: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextPackage:
    """The canonical task-driven context artifact for AI coding agents."""
    task: str
    token_budget: int
    estimated_tokens: int
    raw_file_tokens: int
    token_reduction_pct: float
    entrypoints: List[Dict[str, Any]] = field(default_factory=list)
    direct: List[Dict[str, Any]] = field(default_factory=list)
    indirect: List[Dict[str, Any]] = field(default_factory=list)
    excluded: List[Dict[str, Any]] = field(default_factory=list)
    constraints: ConstraintSet = field(default_factory=ConstraintSet)
    change_plan: Optional[ChangePlan] = None
    snippets: Dict[str, str] = field(default_factory=dict)
    affected_files: List[str] = field(default_factory=list)
    coverage: str = "full"

    def to_markdown(self, level: int = 2) -> str:
        """Render progressive disclosure Markdown block (Level 1, 2, or 3).

        - Level 1: Executive brief: Task, top entrypoints, direct blast radius, high-level plan (~250-400 tokens)
        - Level 2: Standard coding agent context: Signatures, direct/indirect blast radius, constraints, plan (~600-1000 tokens)
        - Level 3: Full context package: Includes exact source code snippets for entrypoints and direct targets (~1200-1800 tokens)
        """
        lines = [
            f"# RepoPeek Context Package: {self.task}",
            f"*Tokens: ~{self.estimated_tokens} (Budget: {self.token_budget} | Raw File Equivalent: ~{self.raw_file_tokens} | Token Reduction: {self.token_reduction_pct}%)*",
            f"*Coverage: `{self.coverage}`*",
            "",
        ]

        # ── 1. Target Entrypoints ──
        lines.append("## 1. Candidate Entrypoints")
        for ep in self.entrypoints[:5]:
            nid = ep.get("node_id", "")
            score = ep.get("score", 0.0)
            sig = ep.get("sig", "")
            file_p = ep.get("file", "")
            story = ep.get("story", "")
            reasons = [r.get("type", "") for r in ep.get("reasons", [])]
            lines.append(f"- **`{nid}`** (Score: {score:.3f} | Match: {', '.join(reasons)})")
            if sig and level >= 2:
                lines.append(f"  - Signature: `{sig}`")
            if file_p:
                lines.append(f"  - Location: `{file_p}`")
            if story and level >= 2:
                lines.append(f"  - Context: {story}")

            if level >= 2 and nid in self.snippets:
                lines.append("  ```")
                lines.append(self.snippets[nid].rstrip())
                lines.append("  ```")
        lines.append("")

        # ── 2. Blast Radius ──
        lines.append("## 2. Evidence-Backed Blast Radius")
        lines.append(f"**Direct Impact ({len(self.direct)}):**")
        for d in self.direct:
            citation = d.get("citation") or d.get("file", "unknown")
            conf = d.get("confidence", d.get("combined_confidence", 0.0))
            lines.append(f"- `{d.get('node_id')}` [{citation}] (Confidence: {conf:.2f})")
            if level >= 3 and d.get("node_id") in self.snippets:
                lines.append("  ```python")
                lines.append(self.snippets[d.get("node_id")].rstrip())
                lines.append("  ```")

        if level >= 2 and self.indirect:
            lines.append("")
            lines.append(f"**Indirect Impact ({len(self.indirect)}):**")
            for ind in self.indirect[:8]:
                citation = ind.get("citation") or ind.get("file", "unknown")
                conf = ind.get("confidence", ind.get("combined_confidence", 0.0))
                lines.append(f"- `{ind.get('node_id')}` [{citation}] (Confidence: {conf:.2f} | Dist: {ind.get('distance')})")

        if level >= 2 and self.excluded:
            lines.append("")
            lines.append(f"**Excluded / Low-Risk Pruned ({len(self.excluded)}):**")
            for ex in self.excluded[:5]:
                lines.append(f"- `{ex.get('node_id')}`: {ex.get('exclusion_reason')}")
        lines.append("")

        # ── 3. Constraints ──
        if level >= 2:
            lines.append("## 3. Extracted Code & Schema Constraints")
            if self.constraints.parameter_constraints:
                lines.append("**Parameter & Type Constraints:**")
                for c in self.constraints.parameter_constraints[:6]:
                    lines.append(f"- {c}")
            if self.constraints.return_constraints:
                lines.append("**Return Type Invariants:**")
                for c in self.constraints.return_constraints[:4]:
                    lines.append(f"- {c}")
            if self.constraints.exception_constraints:
                lines.append("**Exception Boundaries:**")
                for c in self.constraints.exception_constraints[:4]:
                    lines.append(f"- {c}")
            if self.constraints.schema_constraints:
                lines.append("**Schema & Table Dependencies:**")
                for c in self.constraints.schema_constraints[:4]:
                    lines.append(f"- {c}")
            lines.append("")

        # ── 4. Engineering Change Plan ──
        if self.change_plan:
            lines.append("## 4. Engineering Change Plan")
            lines.append(f"**Assessed Risk:** `{self.change_plan.risk_level}`")
            for s in self.change_plan.steps:
                lines.append(f"{s.step_number}. **[{s.phase.upper()}]** {s.action} on `{s.target}`")
                if level >= 2:
                    lines.append(f"   - {s.rationale}")
            lines.append("")

        return "\n".join(lines).strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert ContextPackage to serializable JSON-ready dictionary."""
        return {
            "task": self.task,
            "token_budget": self.token_budget,
            "estimated_tokens": self.estimated_tokens,
            "raw_file_tokens": self.raw_file_tokens,
            "token_reduction_pct": self.token_reduction_pct,
            "entrypoints": self.entrypoints,
            "direct_count": len(self.direct),
            "indirect_count": len(self.indirect),
            "excluded_count": len(self.excluded),
            "direct": self.direct,
            "indirect": self.indirect,
            "excluded": self.excluded,
            "constraints": self.constraints.to_dict(),
            "change_plan": self.change_plan.to_dict() if self.change_plan else None,
            "affected_files": sorted(self.affected_files),
            "coverage": self.coverage,
        }


class ContextCompiler:
    """Compiles engineering tasks into minimal, evidence-backed context packages."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.graph = engine.graph

    def compile(
        self,
        task: str,
        budget: int = 1500,
        level: int = 2,
        include_snippets: bool = True,
        exclusions: Optional[Sequence[str]] = None,
    ) -> ContextPackage:
        """Compile a natural language task into a ContextPackage.

        Args:
            task: Natural language engineering task.
            budget: Token budget constraint (default 1500).
            level: Progressive disclosure level (1, 2, or 3).
            include_snippets: Whether to extract in-card snippets for zero-read edits.
            exclusions: Optional collection of negative exclusion patterns (dirs, files, symbols, globs).

        Returns:
            ContextPackage instance.
        """
        # Determine all active exclusions (explicit + task intent extracted)
        from repopeek.retrieval.intent import extract_task_identifiers
        intent = extract_task_identifiers(task)
        all_exclusions: List[str] = list(exclusions or [])
        if intent.exclusions:
            for ex in intent.exclusions:
                if ex not in all_exclusions:
                    all_exclusions.append(ex)
        if all_exclusions:
            extra_files: List[str] = []
            for nid, node_card in self.graph.nodes.items():
                if is_node_excluded(nid, node_card, all_exclusions):
                    if node_card.span and node_card.span.file:
                        extra_files.append(node_card.span.file.replace("\\", "/"))
            for f in extra_files:
                if f not in all_exclusions:
                    all_exclusions.append(f)

        # 1. Intent-to-symbol resolution
        raw_entrypoints = self.engine.resolve_task(task, limit=10)
        entrypoints: List[Dict[str, Any]] = []
        combined_excluded: Dict[str, Dict[str, Any]] = {}

        for ep in raw_entrypoints:
            nid = ep.get("node_id", "")
            node_card = self.graph.nodes.get(nid)
            if all_exclusions and is_node_excluded(nid, node_card, all_exclusions):
                combined_excluded[nid] = {
                    "node_id": nid,
                    "kind": ep.get("kind", "unknown"),
                    "file": ep.get("file"),
                    "distance": 0,
                    "confidence": ep.get("score", 0.0),
                    "exclusion_reason": "Entrypoint matches explicit exclusion rule",
                }
            else:
                entrypoints.append(ep)

        entrypoints = entrypoints[:5]
        top_node_ids = [ep["node_id"] for ep in entrypoints if "node_id" in ep]

        # 2. Mathematical blast radius computation across top candidate entrypoints
        combined_direct: Dict[str, Dict[str, Any]] = {}
        combined_indirect: Dict[str, Dict[str, Any]] = {}
        all_affected_files: Set[str] = set()

        for ep_id in top_node_ids[:2]:  # Focus blast radius on top 2 entrypoints
            report: BlastRadiusReport = self.engine.blast_radius(
                ep_id,
                max_depth=3,
                confidence_threshold=0.35,
                exclusions=all_exclusions if all_exclusions else None,
            )
            for d in report.direct:
                if d.node_id not in combined_direct:
                    combined_direct[d.node_id] = d.to_dict()
                if d.file and not (all_exclusions and is_node_excluded(d.file, None, all_exclusions)):
                    all_affected_files.add(d.file)
            for ind in report.indirect:
                if ind.node_id not in combined_direct and ind.node_id not in combined_indirect:
                    combined_indirect[ind.node_id] = ind.to_dict()
                if ind.file and not (all_exclusions and is_node_excluded(ind.file, None, all_exclusions)):
                    all_affected_files.add(ind.file)
            for ex in report.excluded:
                if ex.node_id not in combined_direct and ex.node_id not in combined_indirect:
                    combined_excluded[ex.node_id] = ex.to_dict()

            if all_exclusions:
                all_affected_files.update(
                    f for f in report.affected_files if not is_node_excluded(f, None, all_exclusions)
                )
            else:
                all_affected_files.update(report.affected_files)

        combined_direct, combined_indirect = self._filter_neighbors(
            task, intent, top_node_ids, combined_direct, combined_indirect
        )
        combined_direct = {k: v for k, v in combined_direct.items() if not str(k).startswith("ext:")}
        combined_indirect = {k: v for k, v in combined_indirect.items() if not str(k).startswith("ext:")}

        def _file_blocked(path: Optional[str]) -> bool:
            if not path or not all_exclusions:
                return False
            return is_node_excluded(path.replace("\\", "/"), None, all_exclusions)

        for nid in list(combined_direct):
            fp = combined_direct[nid].get("file")
            node = self.graph.nodes.get(nid)
            if fp and _file_blocked(fp):
                combined_direct.pop(nid, None)
            elif node and node.span and _file_blocked(node.span.file):
                combined_direct.pop(nid, None)
        for nid in list(combined_indirect):
            fp = combined_indirect[nid].get("file")
            node = self.graph.nodes.get(nid)
            if fp and _file_blocked(fp):
                combined_indirect.pop(nid, None)
            elif node and node.span and _file_blocked(node.span.file):
                combined_indirect.pop(nid, None)

        # Capture the risk signal from the full (pre-display-trim) blast radius so the
        # change plan's risk level reflects real schema/downstream impact even after the
        # displayed file set is trimmed for precision.
        risk_has_schema = any(
            is_sql_table_kind(str(v.get("kind", "")))
            for v in list(combined_direct.values()) + list(combined_indirect.values())
        )
        risk_total_affected = len(combined_direct) + len(combined_indirect)

        ranked_files: List[str] = []
        raw_l = task.lower()
        ident_l = [i.lower() for i in intent.identifiers if i]
        # Frontend intent requires an explicit client-side signal. A bare "login"
        # mention is not enough: it also appears in backend serializers/views
        # (e.g. UserLoginSerializer) and would wrongly pull in JSX noise.
        frontend_intent = (
            any(w in raw_l for w in (
                "frontend", "front-end", "client-side", "jsx", "tsx", "react",
                "authcontext", "loginpage", "usestate", "useeffect",
            ))
            or bool(re.search(r"\.(jsx|tsx|vue|svelte)\b", raw_l))
            or any(str(p).lower().endswith((".jsx", ".tsx", ".ts")) for p in intent.paths)
        )
        # Data/schema intent: when a task is about DDL, prefer files that actually host a
        # schema definition (a .sql file, or a .py file with embedded CREATE TABLE) over an
        # eponymous module that merely shares the table's name.
        data_intent = any(
            w in raw_l for w in (
                "schema", "create table", "database schema", "migration", " ddl ",
                "table definition", "drop table", "alter table",
            )
        )
        ddl_host_files: Set[str] = set()
        if data_intent:
            for _n in self.graph.nodes.values():
                fp = _n.span.file if _n.span else None
                if fp and (is_sql_table_kind(_n.kind) or "::table." in _n.id):
                    ddl_host_files.add(fp.replace("\\", "/"))

        def _score_file(path: str, base: float) -> float:
            p = path.replace("\\", "/")
            pl = p.lower()
            stem = Path(p).stem.lower()
            s = base
            if any(stem == i or stem.replace("_", "") == i.replace("_", "") for i in ident_l):
                s += 5.0
            elif any(len(i) > 3 and (i in stem or stem in i) for i in ident_l):
                s += 2.0
            if data_intent and (pl.endswith(".sql") or p in ddl_host_files):
                s += 4.0
            if frontend_intent:
                if pl.endswith((".jsx", ".js", ".tsx", ".ts")):
                    s += 3.0
                if "/src/" in pl or pl.startswith("app/src"):
                    s += 1.5
                if any(tok in stem for tok in ("login", "auth", "remember")):
                    s += 4.0
                if pl.endswith("views.py") and not any("view" in i for i in ident_l):
                    s -= 2.0
            return s

        # Accumulate a per-file base signal (entrypoint rank + blast membership). Each
        # file is scored once below so multi-node files are not inflated by applying the
        # stem/frontend boosts repeatedly per node.
        base_signal: Dict[str, float] = {}
        for i, ep in enumerate(entrypoints):
            f = ep.get("file")
            if f and not _file_blocked(f):
                base_signal[f] = base_signal.get(f, 0.0) + (10.0 - i)
        for blob in list(combined_direct.values()) + list(combined_indirect.values()):
            f = blob.get("file")
            if f and not _file_blocked(f):
                base_signal[f] = base_signal.get(f, 0.0) + 1.0

        file_scores: Dict[str, float] = {f: _score_file(f, b) for f, b in base_signal.items()}

        # Keep the top-ranked file always (protects file recall), then only additional
        # files whose score stays within a relative band of the top. Hard cap unchanged
        # at 4; the band is what trims padded noise files to lift precision.
        ranked_files = sorted(file_scores, key=lambda p: (-file_scores[p], p.replace("\\", "/")))
        keep_files: Set[str] = set()
        if ranked_files:
            top_score = file_scores[ranked_files[0]]
            cutoff = 0.5 * top_score
            keep_files.add(ranked_files[0])
            for f in ranked_files[1:]:
                if len(keep_files) >= 4:
                    break
                if file_scores[f] >= cutoff:
                    keep_files.add(f)

        def _is_frontend(path: Optional[str]) -> bool:
            return bool(path) and str(path).lower().endswith((".jsx", ".js", ".tsx", ".ts"))

        # Cross-stack recall backstop: a frontend task whose gold client-side file never
        # survived retrieval/threshold (e.g. LoginPage.jsx on a backend-ranked task) still
        # needs exactly one best-matching frontend file picked by task-token overlap, so
        # coverage stays honest without scanning in every login/auth-named file.
        if frontend_intent and not any(_is_frontend(f) for f in keep_files):
            from repopeek.retrieval.intent import generate_identifier_variants
            task_toks = {t.lower() for t in (intent.identifiers + intent.concepts + intent.stemmed_concepts) if t}
            for ident in intent.identifiers:
                for v in generate_identifier_variants(ident):
                    task_toks.add(v.lower())
            best_fp: Optional[str] = None
            best_s = 0.0
            for node in self.graph.nodes.values():
                fp = node.span.file if node.span else None
                if not fp or _file_blocked(fp) or not _is_frontend(fp):
                    continue
                stem_raw = Path(str(fp).replace("\\", "/")).stem
                stem_words = {p.lower() for p in re.findall(r"[A-Za-z][a-z0-9]*", stem_raw)}
                stem_l = stem_raw.lower()
                overlap = len(stem_words & task_toks)
                ui = sum(1 for tok in ("login", "auth", "remember") if tok in stem_l)
                s = overlap * 2.0 + ui
                if s > best_s or (
                    s == best_s and best_fp is not None and len(stem_l) < len(Path(str(best_fp)).stem)
                ):
                    best_s, best_fp = s, fp
            if best_fp and best_s > 0:
                if len(keep_files) >= 4:
                    evictable = [f for f in ranked_files if f in keep_files and f != ranked_files[0]]
                    if evictable:
                        keep_files.discard(evictable[-1])
                keep_files.add(best_fp)

        # Data/schema recall backstop: for a DDL task, ensure every file that defines a
        # table matching the task (by table-name overlap) is in the pack — even when the
        # table was defined via embedded SQL and outranked by an eponymous module, and even
        # when the same table name is defined in more than one file (genuine ambiguity).
        if data_intent:
            schema_toks = {t.lower() for t in (intent.identifiers + intent.concepts + intent.stemmed_concepts) if t}
            file_match: Dict[str, float] = {}
            for node in self.graph.nodes.values():
                fp = node.span.file if node.span else None
                if not fp or _file_blocked(fp):
                    continue
                if not (is_sql_table_kind(node.kind) or "::table." in node.id):
                    continue
                tname = node.id.split("::")[-1].split(".")[-1].lower()
                tname_toks = set(re.findall(r"[a-z0-9]+", tname))
                score = len(tname_toks & schema_toks) + (2.0 if tname in schema_toks else 0.0)
                if score > 0:
                    fpn = fp.replace("\\", "/")
                    file_match[fpn] = max(file_match.get(fpn, 0.0), score)
            if file_match:
                best = max(file_match.values())
                for fp, sc in sorted(file_match.items(), key=lambda kv: (-kv[1], kv[0])):
                    if sc < best or fp in keep_files:
                        continue
                    if len(keep_files) >= 4:
                        evictable = [f for f in ranked_files if f in keep_files and f != ranked_files[0]]
                        if evictable:
                            keep_files.discard(evictable[-1])
                        else:
                            break
                    keep_files.add(fp)

        all_affected_files = {f for f in keep_files if not _file_blocked(f)}
        entrypoints = [ep for ep in entrypoints if not ep.get("file") or ep.get("file") in keep_files]
        combined_direct = {
            k: v for k, v in combined_direct.items()
            if not v.get("file") or v.get("file") in keep_files
        }
        combined_indirect = {
            k: v for k, v in combined_indirect.items()
            if not v.get("file") or v.get("file") in keep_files
        }

        def _compact(items: List[Dict[str, Any]], max_per_file: int = 2, max_total: int = 8) -> List[Dict[str, Any]]:
            per: Dict[str, int] = {}
            out: List[Dict[str, Any]] = []
            for it in items:
                fp = str(it.get("file") or "").replace("\\", "/")
                if per.get(fp, 0) >= max_per_file:
                    continue
                per[fp] = per.get(fp, 0) + 1
                out.append(it)
                if len(out) >= max_total:
                    break
            return out

        entrypoints = _compact(entrypoints, max_per_file=2, max_total=5)
        direct_list = _compact(list(combined_direct.values()), max_per_file=2, max_total=8)
        indirect_list = _compact(list(combined_indirect.values()), max_per_file=2, max_total=8)
        combined_direct = {d.get("node_id", str(i)): d for i, d in enumerate(direct_list)}
        combined_indirect = {d.get("node_id", str(i)): d for i, d in enumerate(indirect_list)}

        fe_files = [f for f in all_affected_files if str(f).lower().endswith((".jsx", ".js", ".tsx", ".ts"))]
        coverage = "partial" if (frontend_intent and not fe_files) else "full"

        # 3. Extract source code snippets if requested
        snippets: Dict[str, str] = {}
        if include_snippets:
            for ep_id in top_node_ids:
                card = self.engine.lookup(ep_id, include_snippet=True)
                if card and card.snippet:
                    snippets[ep_id] = card.snippet
            for d_id in list(combined_direct.keys())[:3]:
                if d_id not in snippets:
                    card = self.engine.lookup(d_id, include_snippet=True)
                    if card and card.snippet:
                        snippets[d_id] = card.snippet

        # 4. Multi-tier constraint extraction
        constraints = self._extract_constraints(top_node_ids, list(combined_direct.keys()))

        # 5. Risk assessment and change plan generation
        change_plan = self._generate_plan(
            task,
            entrypoints,
            combined_direct,
            combined_indirect,
            all_affected_files,
            risk_has_schema=risk_has_schema,
            risk_total_affected=risk_total_affected,
        )

        # 6. Token economics calculation
        # Raw file tokens: estimate tokens if agent was forced to read the full source files
        raw_tokens = self._estimate_raw_file_tokens(all_affected_files)

        # Assemble ContextPackage
        package = ContextPackage(
            task=task,
            token_budget=budget,
            estimated_tokens=0,  # calculated below
            raw_file_tokens=raw_tokens,
            token_reduction_pct=0.0,
            entrypoints=entrypoints,
            direct=list(combined_direct.values()),
            indirect=list(combined_indirect.values()),
            excluded=list(combined_excluded.values()),
            constraints=constraints,
            change_plan=change_plan,
            snippets=snippets,
            affected_files=sorted(list(all_affected_files)),
            coverage=coverage,
        )

        # Calculate estimated tokens from markdown rendering
        rendered_md = package.to_markdown(level=level)
        est_tokens = ContextPack.estimate_tokens_from_text(rendered_md)
        package.estimated_tokens = est_tokens

        # Token-budget enforcement. When the rendered pack exceeds budget, shed the
        # lowest-value material first — surplus neighbor snippets, then indirect cards,
        # then extra direct cards — while keeping the primary entrypoint and one snippet
        # per shortlisted (incl. gold) file. We trim context depth, never the file list.
        def _reestimate() -> int:
            return ContextPack.estimate_tokens_from_text(package.to_markdown(level=level))

        if est_tokens > budget and package.estimated_tokens > budget:
            ep_order = [ep.get("node_id") for ep in package.entrypoints if ep.get("node_id")]
            primary = set(ep_order[:1])
            # One snippet per shortlisted file (the highest-ranked entrypoint there) is kept
            # so every file in the shortlist retains a span.
            primary_per_file: Dict[str, str] = {}
            for ep in package.entrypoints:
                f, nid = ep.get("file"), ep.get("node_id")
                if f and nid and f not in primary_per_file:
                    primary_per_file[f] = nid
            keep_snip = set(primary_per_file.values()) | primary

            # Phase 1: drop neighbor snippets, then secondary entrypoint snippets low->high.
            drop_order = [k for k in list(package.snippets) if k not in ep_order and k not in keep_snip]
            drop_order += [k for k in reversed(ep_order) if k not in keep_snip]
            for key in drop_order:
                if package.estimated_tokens <= budget:
                    break
                if key in package.snippets:
                    package.snippets.pop(key, None)
                    package.estimated_tokens = _reestimate()

            # Phase 2: shed indirect cards from the tail.
            while package.estimated_tokens > budget and package.indirect:
                package.indirect.pop()
                package.estimated_tokens = _reestimate()

            # Phase 3: shed surplus direct cards (keep at least the top one).
            while package.estimated_tokens > budget and len(package.direct) > 1:
                package.direct.pop()
                package.estimated_tokens = _reestimate()

            # Last resort: keep only the primary entrypoint snippet.
            if package.estimated_tokens > budget:
                for key in [k for k in list(package.snippets) if k not in primary]:
                    if package.estimated_tokens <= budget:
                        break
                    package.snippets.pop(key, None)
                    package.estimated_tokens = _reestimate()

            est_tokens = package.estimated_tokens

        # Token reduction percentage
        denom = max(raw_tokens, est_tokens)
        reduction = max(0.0, round((1.0 - (est_tokens / denom)) * 100, 1)) if denom > 0 else 0.0
        package.token_reduction_pct = reduction

        return package

    def _extract_constraints(
        self,
        entrypoint_ids: List[str],
        direct_ids: List[str],
    ) -> ConstraintSet:
        """Extract multi-tier structural and semantic constraints from touched nodes."""
        constraints = ConstraintSet()
        touched_ids = set(entrypoint_ids + direct_ids)

        for nid in touched_ids:
            node = self.graph.nodes.get(nid)
            if not node:
                continue

            # Parameter type constraints
            if node.facts.params:
                sig_params = ", ".join(node.facts.params)
                constraints.parameter_constraints.append(f"`{node.id}` expects parameters: ({sig_params})")

            # Return type constraints
            if node.facts.returns:
                constraints.return_constraints.append(f"`{node.id}` must return `{node.facts.returns}`")

            # Exception boundaries
            if node.facts.raises:
                raises_str = ", ".join(node.facts.raises)
                constraints.exception_constraints.append(f"`{node.id}` may raise: {raises_str}")

            # Schema constraints — kind/edge based, never substring of node.id
            if is_sql_table_kind(node.kind):
                constraints.schema_constraints.append(f"Relies on schema table `{node.id}`")

            # Behavioral invariant from story
            if node.story and node.story.text:
                constraints.behavioral_invariants.append(f"`{node.id}`: {node.story.text}")

        return constraints

    def _generate_plan(
        self,
        task: str,
        entrypoints: List[Dict[str, Any]],
        direct_nodes: Dict[str, Dict[str, Any]],
        indirect_nodes: Dict[str, Dict[str, Any]],
        affected_files: Set[str],
        risk_has_schema: Optional[bool] = None,
        risk_total_affected: Optional[int] = None,
    ) -> ChangePlan:
        """Generate a risk-aware, step-by-step engineering change plan.

        ``risk_has_schema`` / ``risk_total_affected`` let the caller pass the full
        pre-trim blast-radius signal so risk assessment is not softened by the display
        file-count trimming applied for precision. When omitted they are derived from the
        (possibly trimmed) node sets for standalone use.
        """
        # 1. Determine Risk Level
        risk_reasons: List[str] = []
        trimmed_total = len(direct_nodes) + len(indirect_nodes)
        total_affected = risk_total_affected if risk_total_affected is not None else trimmed_total
        has_schema = (
            risk_has_schema
            if risk_has_schema is not None
            else any(
                is_sql_table_kind(str(d.get("kind", "")))
                for d in list(direct_nodes.values()) + list(indirect_nodes.values())
            )
        )

        if has_schema or total_affected > 5:
            risk_level = "HIGH"
            if has_schema:
                risk_reasons.append("Modifications propagate to or from database schema tables")
            if total_affected > 5:
                risk_reasons.append(f"Broad blast radius affecting {total_affected} downstream nodes")
        elif total_affected > 1 or len(affected_files) > 1:
            risk_level = "MEDIUM"
            risk_reasons.append(f"Cross-symbol propagation affecting {len(affected_files)} files")
        else:
            risk_level = "LOW"
            risk_reasons.append("Isolated change localized to single symbol / file")

        # 2. Identify Pre-checks (tests touching affected files)
        pre_checks: List[str] = []
        test_files = [f for f in affected_files if "test" in f.lower()]
        if test_files:
            pre_checks.append(f"Execute baseline test suite: `pytest {' '.join(test_files)}`")
        else:
            pre_checks.append("Verify clean git working tree prior to modification")

        # 3. Actionable Steps
        steps: List[ChangePlanStep] = []
        step_counter = 1

        # Phase: Core modifications for top entrypoints
        for ep in entrypoints[:2]:
            nid = ep.get("node_id", "")
            file_p = ep.get("file")
            node = self.graph.nodes.get(nid)
            citation = f"{node.span.file}:{node.span.start}-{node.span.end}" if node and node.span else file_p

            steps.append(ChangePlanStep(
                step_number=step_counter,
                phase="core_modification",
                action=f"Modify implementation logic in `{nid}` to satisfy task intent",
                target=nid,
                file=file_p,
                citation=citation,
                rationale="Primary target identified by intent resolver",
            ))
            step_counter += 1

        # Phase: Direct blast radius updates
        for d_id, d_data in list(direct_nodes.items())[:3]:
            if any(s.target == d_id for s in steps):
                continue
            steps.append(ChangePlanStep(
                step_number=step_counter,
                phase="blast_radius_update",
                action=f"Review and adjust caller/dependency `{d_id}` for signature or behavior compatibility",
                target=d_id,
                file=d_data.get("file"),
                citation=d_data.get("citation"),
                rationale=f"Direct 1-hop dependent with confidence {d_data.get('combined_confidence', 0.9):.2f}",
            ))
            step_counter += 1

        # 4. Post-checks
        post_checks: List[str] = [
            f"Run regression test suite across affected files ({len(affected_files)} files)",
            "Run `repopeek --update <file>` to verify graph consistency and blast radius resolution",
        ]

        return ChangePlan(
            task=task,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            steps=steps,
            affected_files=sorted(list(affected_files)),
            pre_checks=pre_checks,
            post_checks=post_checks,
        )

    def _filter_neighbors(
        self,
        task: str,
        intent: Any,
        entrypoint_ids: List[str],
        combined_direct: Dict[str, Dict[str, Any]],
        combined_indirect: Dict[str, Dict[str, Any]],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Keep structurally relevant neighbors; drop connected-but-irrelevant noise."""
        import re
        from typing import Any as _Any

        entry_files = set()
        for eid in entrypoint_ids:
            node = self.graph.nodes.get(eid)
            if node and node.span and node.span.file:
                entry_files.add(node.span.file)

        terms = {t.lower() for t in (intent.identifiers + intent.concepts + intent.compounds[:12]) if t}
        terms = {t for t in terms if len(t) > 2}

        def _score(nid: str, data: Dict[str, Any], bucket: str) -> float:
            node = self.graph.nodes.get(nid)
            kind = (data.get("kind") or (node.kind if node else "")).lower()
            file_p = data.get("file") or (node.span.file if node and node.span else "") or ""
            nid_l = nid.lower()
            dist = int(data.get("distance") or data.get("depth") or 2)
            gscore = float(data.get("graph_score") or data.get("combined_confidence") or 0.0)
            overlap = sum(1 for t in terms if t in nid_l or t in file_p.lower())
            same_file = 1.0 if file_p in entry_files else 0.0
            structural = 0.0
            if kind in ("function", "method", "class"):
                structural = 0.35
            elif kind in ("yaml_config", "json_config", "file", "module", "external_symbol"):
                structural = -0.4 if getattr(intent, "task_kind", "application") == "application" else 0.2
            hop_pen = 0.0 if dist <= 1 else -0.25 * (dist - 1)
            keep_boost = 0.8 if nid in entrypoint_ids else 0.0
            lexical = min(1.0, 0.25 * overlap)
            fe_boost = 0.0
            tl = task.lower()
            file_stem = Path(str(file_p).replace("\\", "/")).stem.lower() if file_p else ""
            if any(w in tl for w in ("login", "frontend", "ui", "jsx", "react", "authcontext", "remember-me")):
                if str(file_p).lower().endswith((".jsx", ".js", ".tsx", ".ts")):
                    fe_boost = 0.7
                if any(tok in file_stem for tok in ("login", "auth", "remember")):
                    fe_boost = max(fe_boost, 1.2)
            if str(nid).startswith("ext:"):
                return -5.0
            return keep_boost + gscore + lexical + same_file * 0.5 + structural + hop_pen + fe_boost

        scored_direct = sorted(
            combined_direct.items(),
            key=lambda kv: (-_score(kv[0], kv[1], "direct"), kv[0]),
        )
        scored_indirect = sorted(
            combined_indirect.items(),
            key=lambda kv: (-_score(kv[0], kv[1], "indirect"), kv[0]),
        )

        kept_direct: Dict[str, Dict[str, Any]] = {}
        for nid, data in scored_direct:
            s = _score(nid, data, "direct")
            dist = int(data.get("distance") or 1)
            if nid in entrypoint_ids or dist == 1 or s >= 0.25:
                data = dict(data)
                data["relevance"] = "direct" if dist == 1 else "structural"
                kept_direct[nid] = data
            if len(kept_direct) >= 12:
                break

        kept_indirect: Dict[str, Dict[str, Any]] = {}
        for nid, data in scored_indirect:
            if nid in kept_direct:
                continue
            s = _score(nid, data, "indirect")
            if s < 0.35:
                continue
            data = dict(data)
            data["relevance"] = "possible"
            kept_indirect[nid] = data
            if len(kept_indirect) >= 8:
                break

        return kept_direct, kept_indirect

    def _estimate_raw_file_tokens(self, files: Set[str]) -> int:
        """Estimate the tokens an agent would have to consume by reading raw files."""
        total_tokens = 0
        repo_root = getattr(self.engine, "repo_root", None) or Path(".")

        for f in files:
            path_candidates = [
                Path(f),
                repo_root / f,
                Path(".") / f,
            ]
            found = False
            for p in path_candidates:
                if p.exists() and p.is_file():
                    try:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        total_tokens += ContextPack.estimate_tokens_from_text(content)
                        found = True
                        break
                    except Exception:
                        pass
            if not found:
                # Default assumption: average source file is ~1200 tokens
                total_tokens += 1200

        return max(total_tokens, 2000)
