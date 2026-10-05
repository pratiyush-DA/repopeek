"""Task-to-symbol intent resolution: normalization, identifier extraction, variant generation, and RRF.

Implements the deterministic retrieval pipeline described in the Phase 3 architecture spec:
  Task -> Normalize -> Extract identifiers -> Generate variants -> AST search + FTS5 BM25 -> RRF -> Candidates.

Operates completely offline without LLM, GPU, or vector DB.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# ── Stop words for filtering natural language noise from task queries ──
_STOP_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "and", "or", "but", "if", "then", "else", "when", "where", "how", "why",
    "not", "no", "nor", "so", "too", "very", "just", "also", "only",
    "in", "on", "at", "to", "for", "of", "with", "from", "by", "as", "into",
    "about", "after", "before", "between", "through", "during", "above",
    "below", "up", "down", "out", "off", "over", "under",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "than", "own", "same",
}

# ── Code-action verbs that indicate intent but are not symbol identifiers ──
_ACTION_VERBS: Set[str] = {
    "add", "change", "modify", "update", "fix", "refactor", "remove", "delete",
    "implement", "create", "replace", "rename", "move", "extract", "split",
    "merge", "debug", "investigate", "check", "verify", "validate", "test",
    "handle", "support", "enable", "disable", "increase", "decrease", "set",
    "get", "make", "ensure", "allow", "prevent", "improve", "optimize",
}

# ── Regex patterns for detecting explicit code references in task text ──
_DOTTED_NAME_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
_QUOTED_RE = re.compile(r"[`'\"]([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)[`'\"]")
_PATH_RE = re.compile(r"[\w./\\]+\.\w{1,5}")
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SNAKE_RE = re.compile(r"[a-z_][a-z0-9_]*(?:_[a-z0-9]+)+")
_CONSTANT_RE = re.compile(r"[A-Z][A-Z0-9_]{2,}")
_NUMBER_RE = re.compile(r"\b\d+\b")
_API_PATH_RE = re.compile(r"/[a-z0-9_/{}:]+")


@dataclass
class TaskIntent:
    """Structured extraction of identifiers and domain terms from a natural language task."""
    raw: str
    normalized: str
    identifiers: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    verbs: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    api_paths: List[str] = field(default_factory=list)
    dotted_names: List[str] = field(default_factory=list)
    quoted_names: List[str] = field(default_factory=list)


@dataclass
class SymbolCandidate:
    """A candidate symbol returned by the intent resolver with explanation."""
    node_id: str
    score: float
    reasons: List[Dict[str, Any]] = field(default_factory=list)


def normalize_task_text(task: str) -> str:
    """Normalize task text for retrieval: lowercase, strip punctuation, collapse whitespace."""
    text = task.strip()
    # Preserve dotted names and quoted identifiers before lowercasing
    text = re.sub(r"[^\w\s./'\"`:_\-/{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_camel_case(name: str) -> List[str]:
    """Split CamelCase identifier into component words."""
    parts = _CAMEL_SPLIT_RE.split(name)
    return [p.lower() for p in parts if p]


def _split_snake_case(name: str) -> List[str]:
    """Split snake_case identifier into component words."""
    return [p.lower() for p in name.split("_") if p]


def generate_identifier_variants(name: str) -> List[str]:
    """Generate normalized variants of an identifier for fuzzy matching.

    Example: 'paymentRetryCount' -> ['paymentRetryCount', 'payment_retry_count',
             'payment retry count', 'retryCount', 'retry_count', 'retry', 'payment']
    """
    variants: List[str] = [name]
    name_lower = name.lower()

    # Already snake_case
    if "_" in name:
        parts = _split_snake_case(name)
        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
        variants.append(camel)
        variants.append(" ".join(parts))
        variants.append(name_lower)
        # Suffixes of decreasing length
        for i in range(1, len(parts)):
            suffix_snake = "_".join(parts[i:])
            variants.append(suffix_snake)
    # CamelCase
    elif any(c.isupper() for c in name[1:]):
        parts = _split_camel_case(name)
        snake = "_".join(parts)
        variants.append(snake)
        variants.append(" ".join(parts))
        variants.append(name_lower)
        # Suffixes
        for i in range(1, len(parts)):
            suffix_parts = parts[i:]
            variants.append("_".join(suffix_parts))
            variants.append(suffix_parts[0] + "".join(p.capitalize() for p in suffix_parts[1:]))
    else:
        variants.append(name_lower)

    # Dotted name decomposition
    if "." in name:
        dot_parts = name.split(".")
        for dp in dot_parts:
            variants.append(dp)
            variants.append(dp.lower())

    # Deduplicate while preserving order
    seen: Set[str] = set()
    unique: List[str] = []
    for v in variants:
        vl = v.lower()
        if vl not in seen and len(vl) > 1:
            seen.add(vl)
            unique.append(v)
    return unique


def extract_task_identifiers(task: str) -> TaskIntent:
    """Extract structured identifiers, domain terms, and explicit code refs from a task.

    Prioritizes explicit code references (dotted names, quoted identifiers, paths)
    over natural language tokens.
    """
    normalized = normalize_task_text(task)
    intent = TaskIntent(raw=task, normalized=normalized)

    # 1. Extract quoted code references (highest signal)
    for m in _QUOTED_RE.finditer(task):
        intent.quoted_names.append(m.group(1))

    # 2. Extract dotted names (e.g., PaymentService.retry)
    for m in _DOTTED_NAME_RE.finditer(task):
        name = m.group()
        # Skip file paths (contain / or \)
        if "/" not in name and "\\" not in name:
            intent.dotted_names.append(name)

    # 3. Extract file paths
    for m in _PATH_RE.finditer(task):
        path = m.group()
        if "/" in path or "\\" in path or path.count(".") == 1:
            intent.paths.append(path)

    # 4. Extract API paths
    for m in _API_PATH_RE.finditer(task):
        intent.api_paths.append(m.group())

    # 5. Extract numeric values
    for m in _NUMBER_RE.finditer(task):
        intent.values.append(m.group())

    # 6. Tokenize for identifiers and concepts
    tokens = re.findall(r"[A-Za-z_]\w*", normalized)
    for token in tokens:
        token_lower = token.lower()
        if token_lower in _STOP_WORDS:
            continue

        # Action verbs
        if token_lower in _ACTION_VERBS:
            intent.verbs.append(token_lower)
            continue

        # CONSTANTS
        if _CONSTANT_RE.fullmatch(token):
            intent.identifiers.append(token)
            continue

        # CamelCase or mixedCase identifiers (e.g. PaymentProcessor, retryCount)
        if any(c.isupper() for c in token[1:]):
            intent.identifiers.append(token)
            continue

        # snake_case identifiers (detected as single token if underscore preserved)
        if "_" in token:
            intent.identifiers.append(token)
            continue

        # Remaining technical nouns (length > 2 to filter noise)
        if len(token_lower) > 2:
            intent.concepts.append(token_lower)

    # Promote quoted and dotted names to identifiers
    for name in intent.quoted_names + intent.dotted_names:
        if name not in intent.identifiers:
            intent.identifiers.append(name)

    return intent


def _build_fts_query(intent: TaskIntent) -> str:
    """Build an SQLite FTS5 query string from extracted task identifiers.

    Uses OR-based matching with identifier tokens weighted highest.
    """
    terms: List[str] = []

    # Highest priority: exact identifiers, dotted names, quoted names
    for ident in intent.identifiers:
        # For dotted names, search each component
        if "." in ident:
            for part in ident.split("."):
                part_clean = re.sub(r"[^\w]", "", part)
                if part_clean and len(part_clean) > 1:
                    terms.append(part_clean)
        else:
            clean = re.sub(r"[^\w]", "", ident)
            if clean:
                terms.append(clean)
                # Also add CamelCase/snake_case variants
                for v in generate_identifier_variants(clean):
                    v_clean = re.sub(r"[^\w]", "", v)
                    if v_clean and len(v_clean) > 1:
                        terms.append(v_clean)

    # Medium priority: domain concepts
    for concept in intent.concepts:
        clean = re.sub(r"[^\w]", "", concept)
        if clean and len(clean) > 2:
            terms.append(clean)

    # Deduplicate preserving order
    seen: Set[str] = set()
    unique_terms: List[str] = []
    for t in terms:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            unique_terms.append(t)

    if not unique_terms:
        return ""

    # FTS5 OR query
    return " OR ".join(unique_terms)


def _ast_identifier_search(
    intent: TaskIntent,
    node_index: Dict[str, Any],
    limit: int = 30,
) -> List[Tuple[str, float]]:
    """Direct AST identifier matching against node IDs, signatures, and stories.

    Returns list of (node_id, score) tuples ranked by match quality.
    """
    # Build variant sets from all extracted identifiers
    search_terms: List[str] = []
    for ident in intent.identifiers:
        search_terms.extend(generate_identifier_variants(ident))
    for concept in intent.concepts:
        search_terms.append(concept)

    search_terms_lower = {t.lower() for t in search_terms if len(t) > 1}
    if not search_terms_lower:
        return []

    scored: Dict[str, float] = {}

    for node_id, node_data in node_index.items():
        node_id_lower = node_id.lower()
        sig_lower = (node_data.get("sig") or "").lower()
        story_lower = (node_data.get("story_text") or "").lower()

        score = 0.0
        for term in search_terms_lower:
            # Exact ID suffix match (strongest signal)
            if node_id_lower.endswith(f"::{term}") or node_id_lower.endswith(f".{term}"):
                score += 5.0
            # ID contains term
            elif term in node_id_lower:
                score += 3.0
            # Signature match
            if term in sig_lower:
                score += 4.0
            # Story match
            if term in story_lower:
                score += 1.0

        if score > 0:
            scored[node_id] = score

    # Sort by score descending, return top-N
    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return ranked[:limit]


def reciprocal_rank_fusion(
    *ranked_lists: List[Tuple[str, float]],
    k: int = 60,
    weights: Optional[List[float]] = None,
) -> List[Tuple[str, float]]:
    """Combine multiple ranked result lists using Reciprocal Rank Fusion.

    RRF(d) = sum_r  weight_r / (k + rank_r(d))

    Args:
        ranked_lists: Variable number of ranked (id, score) lists.
        k: RRF constant (default 60 per specification).
        weights: Optional per-retriever weights. Defaults to equal weights.

    Returns:
        Fused ranked list of (id, rrf_score) tuples sorted descending.
    """
    if not ranked_lists:
        return []

    if weights is None:
        weights = [1.0] * len(ranked_lists)

    fused_scores: Dict[str, float] = {}

    for retriever_idx, ranked in enumerate(ranked_lists):
        w = weights[retriever_idx] if retriever_idx < len(weights) else 1.0
        for rank_pos, (item_id, _original_score) in enumerate(ranked):
            rrf_contribution = w / (k + rank_pos + 1)  # rank is 1-indexed
            fused_scores[item_id] = fused_scores.get(item_id, 0.0) + rrf_contribution

    return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)


def resolve_task_to_symbols(
    task: str,
    node_index: Dict[str, Any],
    fts_results: Optional[List[Tuple[str, float]]] = None,
    limit: int = 20,
) -> List[SymbolCandidate]:
    """Resolve a natural language task to ranked candidate symbols.

    Three-stage pipeline:
    1. Extract and normalize task identifiers
    2. AST identifier search (always available, deterministic)
    3. FTS5 BM25 results (if SQLite cache available)
    4. RRF fusion to produce final ranked candidates

    Args:
        task: Natural language engineering task text.
        node_index: Dict mapping node_id -> {sig, story_text, kind, file} for AST search.
        fts_results: Pre-computed FTS5 BM25 results as (node_id, bm25_score) tuples.
        limit: Maximum number of candidates to return.

    Returns:
        Ranked list of SymbolCandidate objects with scores and reasoning.
    """
    intent = extract_task_identifiers(task)

    # Stage 1: AST identifier search (always works, deterministic)
    ast_results = _ast_identifier_search(intent, node_index, limit=50)

    # Stage 2: FTS5 BM25 (provided externally from SQLite)
    fts_ranked = fts_results or []

    # Stage 3: RRF fusion
    # Weight AST identifier matches higher than BM25 per spec (1.0 vs 0.9)
    retriever_lists = [ast_results]
    retriever_weights = [1.0]

    if fts_ranked:
        retriever_lists.append(fts_ranked)
        retriever_weights.append(0.9)

    fused = reciprocal_rank_fusion(*retriever_lists, k=60, weights=retriever_weights)

    # Build SymbolCandidate objects with reasoning
    ast_ids = {nid for nid, _ in ast_results}
    fts_ids = {nid for nid, _ in fts_ranked}

    candidates: List[SymbolCandidate] = []
    for node_id, rrf_score in fused[:limit]:
        reasons: List[Dict[str, Any]] = []

        if node_id in ast_ids:
            ast_score = next(s for nid, s in ast_results if nid == node_id)
            reasons.append({"type": "identifier_match", "score": round(ast_score, 3)})

        if node_id in fts_ids:
            fts_score = next(s for nid, s in fts_ranked if nid == node_id)
            reasons.append({"type": "bm25", "score": round(fts_score, 3)})

        candidates.append(SymbolCandidate(
            node_id=node_id,
            score=round(rrf_score, 6),
            reasons=reasons,
        ))

    return candidates
