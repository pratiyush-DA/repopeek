"""Anti-hallucination fact verifier cross-checking LLM stories against AST facts."""

from dataclasses import dataclass, field
import re
from typing import List, Literal

from repopeek.models.schema import NodeCard, NodeFacts


@dataclass
class VerificationResult:
    """Outcome of validating a candidate story against deterministic AST facts."""
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    confidence: Literal["high", "medium", "low", "dynamic", "unresolved"] = "high"


class FactVerifier:
    """Validates that candidate LLM stories do not hallucinate unverified behaviors."""

    MAX_WORD_COUNT = 60

    def verify(self, node: NodeCard, candidate_text: str) -> VerificationResult:
        """Validate candidate story against node AST facts and signature constraints."""
        text = candidate_text.strip()
        issues: List[str] = []

        # 1. Non-empty check
        if not text:
            return VerificationResult(is_valid=False, issues=["Story text is empty"], confidence="low")

        # 2. Length check (must be a concise one-line narrative for low-context agents)
        words = text.split()
        if len(words) > self.MAX_WORD_COUNT:
            issues.append(f"Story exceeds maximum word count ({len(words)} > {self.MAX_WORD_COUNT})")

        # 3. Detect raw code or markdown block dumps
        if "```" in text or text.startswith("def ") or text.startswith("class "):
            issues.append("Story contains raw code or markdown code blocks instead of narrative")

        # 4. Detect hallucinated database table references
        table_pattern = re.compile(r"\b(?:table|relation|queries|from)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", re.IGNORECASE)
        for match in table_pattern.finditer(text):
            tbl = match.group(1).lower().rstrip(".,;:")
            # Ignore common generic English words
            if tbl in ("a", "the", "an", "this", "each", "all", "its", "sql", "data", "records"):
                continue
            # Check against facts.reads and facts.writes
            known_entities = {
                e.lower().split("::")[-1].replace("table.", "")
                for e in (node.facts.reads + node.facts.writes)
            }
            if (not known_entities) or (not any(tbl in ke or ke in tbl for ke in known_entities)):
                issues.append(f"Hallucinated table or entity reference: '{tbl}' not in AST facts")

        # 5. Check if node has 0 calls but story claims multiple complex external calls
        if node.facts.calls == 0 and any(
            phrase in text.lower() for phrase in ("calls service", "invokes api", "sends http", "executes command")
        ):
            issues.append("Story claims external service invocation but node AST contains 0 function calls")

        if issues:
            return VerificationResult(is_valid=False, issues=issues, confidence="low")

        return VerificationResult(is_valid=True, issues=[], confidence="high")
