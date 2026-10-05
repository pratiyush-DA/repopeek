"""Context Compiler, Constraint Extractor, and Change Plan Generator.

Implements the Phase 3 Context Compiler specification:
Compiles high-level natural language engineering tasks into minimal, evidence-backed
Context Packages with multi-tier constraint enforcement, quantitative blast radius,
and risk-aware step-by-step change plans.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from repopeek.graph.blast_radius import BlastRadiusReport, compute_blast_radius, is_node_excluded
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

    def to_markdown(self, level: int = 2) -> str:
        """Render progressive disclosure Markdown block (Level 1, 2, or 3).

        - Level 1: Executive brief: Task, top entrypoints, direct blast radius, high-level plan (~250-400 tokens)
        - Level 2: Standard coding agent context: Signatures, direct/indirect blast radius, constraints, plan (~600-1000 tokens)
        - Level 3: Full context package: Includes exact source code snippets for entrypoints and direct targets (~1200-1800 tokens)
        """
        lines = [
            f"# RepoPeek Context Package: {self.task}",
            f"*Tokens: ~{self.estimated_tokens} (Budget: {self.token_budget} | Raw File Equivalent: ~{self.raw_file_tokens} | Token Reduction: {self.token_reduction_pct}%)*",
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

            # Include snippet if level 3
            if level >= 3 and nid in self.snippets:
                lines.append("  ```python")
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
        change_plan = self._generate_plan(task, entrypoints, combined_direct, combined_indirect, all_affected_files)

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
        )

        # Calculate estimated tokens from markdown rendering
        rendered_md = package.to_markdown(level=level)
        est_tokens = ContextPack.estimate_tokens_from_text(rendered_md)
        package.estimated_tokens = est_tokens

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

            # Schema constraints
            if "table" in node.id or node.kind == "sql_table":
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
    ) -> ChangePlan:
        """Generate a risk-aware, step-by-step engineering change plan."""
        # 1. Determine Risk Level
        risk_reasons: List[str] = []
        total_affected = len(direct_nodes) + len(indirect_nodes)
        has_schema = any("table" in nid for nid in list(direct_nodes.keys()) + list(indirect_nodes.keys()))

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
