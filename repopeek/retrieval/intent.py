"""Task-to-symbol intent resolution: normalization, identifier extraction, variant generation, and RRF.

Implements the deterministic retrieval pipeline described in the Phase 3 and PR20 architecture specs:
  Task -> Normalize -> Extract identifiers -> Generate variants -> AST search + FTS5 BM25 -> Multi-component ranking -> Candidates.

Operates completely offline without LLM, GPU, or vector DB.
"""

from collections import defaultdict
from dataclasses import dataclass, field
import fnmatch
import re
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
    "such", "than", "own", "same", "without", "against",
}

# ── Pure operational verbs that indicate user intent but rarely match code symbols ──
_OPERATIONAL_VERBS: Set[str] = {
    "add", "change", "modify", "update", "fix", "refactor", "remove", "delete",
    "implement", "create", "replace", "rename", "move", "increase", "decrease",
    "make", "ensure", "allow", "prevent", "improve", "optimize", "adjust",
}

# ── Technical code action verbs that frequently appear in function/method identifiers ──
_TECHNICAL_VERBS: Set[str] = {
    "validate", "parse", "test", "check", "verify", "handle", "support",
    "enable", "disable", "set", "get", "extract", "split", "merge",
    "debug", "investigate", "trace", "mine", "build", "route", "normalize",
    "resolve", "compute", "calculate", "find", "load", "save", "write", "read",
}

_ACTION_VERBS: Set[str] = _OPERATIONAL_VERBS | _TECHNICAL_VERBS

# ── Regex patterns for detecting explicit code references in task text ──
_DOTTED_NAME_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
_QUOTED_RE = re.compile(r"[`'\"]([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)[`'\"]")
_PATH_RE = re.compile(r"[\w./\\]+\.\w{1,5}")
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SNAKE_RE = re.compile(r"[a-z_][a-z0-9_]*(?:_[a-z0-9]+)+")
_CONSTANT_RE = re.compile(r"[A-Z][A-Z0-9_]{2,}")
_NUMBER_RE = re.compile(r"\b\d+\b")
_API_PATH_RE = re.compile(r"/[a-z0-9_/{}:]+")

# Pattern for capturing negative exclusions in task prompts (e.g. 'without modifying shipping', 'do not touch X')
_EXCLUSION_PATTERN = re.compile(
    r"(?:without|not|avoid|except|excluding)\s+(?:modifying|changing|altering|touching|updating|including)?\s*([A-Za-z0-9_./\\-]+)",
    re.IGNORECASE,
)


@dataclass
class TaskIntent:
    """Structured extraction of identifiers, domain terms, and negative constraints from a task."""
    raw: str
    normalized: str
    identifiers: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    stemmed_concepts: List[str] = field(default_factory=list)
    compounds: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    verbs: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    api_paths: List[str] = field(default_factory=list)
    dotted_names: List[str] = field(default_factory=list)
    quoted_names: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)


@dataclass
class RetrievalScore:
    """Explicit, testable component breakdown of symbol retrieval scoring."""
    exact_match: float = 0.0       # Exact match on symbol URI or qualified name [0..1]
    identifier: float = 0.0        # Identifier variant and component token match [0..1]
    token_overlap: float = 0.0     # Query concept coverage in symbol name/sig/story [0..1]
    lexical: float = 0.0           # FTS5 BM25 normalized score [0..1]
    path_relevance: float = 0.0    # File path / module relevance [0..1]
    kind_preference: float = 0.0   # Method/function/class preference over file/type cards [0..1]

    @property
    def total(self) -> float:
        """Calibrated linear combination of normalized components."""
        return round(
            0.35 * self.exact_match
            + 0.25 * self.identifier
            + 0.20 * self.token_overlap
            + 0.10 * self.lexical
            + 0.05 * self.path_relevance
            + 0.05 * self.kind_preference,
            6,
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "exact_match": round(self.exact_match, 4),
            "identifier": round(self.identifier, 4),
            "token_overlap": round(self.token_overlap, 4),
            "lexical": round(self.lexical, 4),
            "path_relevance": round(self.path_relevance, 4),
            "kind_preference": round(self.kind_preference, 4),
            "total": round(self.total, 4),
        }


@dataclass
class SymbolCandidate:
    """A candidate symbol returned by the intent resolver with explanation."""
    node_id: str
    score: float
    reasons: List[Dict[str, Any]] = field(default_factory=list)
    breakdown: Optional[Dict[str, float]] = None


def normalize_term_stem(word: str) -> str:
    """Conservative, deterministic linguistic normalization for code search terms.

    Applies standard suffix normalizations without over-stemming.
    Examples:
      - 'retrying' / 'retried' / 'retries' -> 'retry'
      - 'payments' -> 'payment'
      - 'processors' / 'processing' -> 'process'
      - 'validators' / 'validating' / 'validation' -> 'validate'
      - 'parsers' / 'parsing' -> 'parse'
      - 'connections' / 'connecting' -> 'connect'
      - 'configurations' / 'configuring' -> 'config'
    """
    w = word.strip().lower()
    if len(w) <= 3:
        return w

    # Engineering synonym mapping (high precision)
    synonym_map = {
        "configuration": "config",
        "configure": "config",
        "configuring": "config",
        "configured": "config",
        "authentication": "auth",
        "authenticate": "auth",
        "authenticating": "auth",
        "initialization": "init",
        "initialize": "init",
        "initializing": "init",
        "specification": "spec",
        "specifications": "spec",
        "parameters": "param",
        "parameter": "param",
    }
    if w in synonym_map:
        return synonym_map[w]

    # Plural -ies (e.g. retries -> retry, queries -> query, dependencies -> dependency)
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"

    # Plural -es after s, x, z, ch, sh (e.g. watches -> watch, boxes -> box, processes -> process)
    if (w.endswith("sses") or w.endswith("shes") or w.endswith("ches") or w.endswith("xes")) and len(w) > 4:
        return w[:-2]

    # Standard plural -s (e.g. payments -> payment, attempts -> attempt, endpoints -> endpoint)
    # Exclude words ending in 'ss', 'us', 'is' (e.g. class, status, basis)
    if w.endswith("s") and not w.endswith("ss") and not w.endswith("us") and not w.endswith("is"):
        stem = w[:-1]
        if len(stem) >= 3:
            w = stem

    # Suffix -ation / -ition (e.g. validation -> validate, calculation -> calculate, expiration -> expire)
    if w.endswith("ation") and len(w) > 6:
        return w[:-5] + "ate"
    if w.endswith("ition") and len(w) > 6:
        return w[:-5] + "ite"

    # Suffix -tion (e.g. connection -> connect, extraction -> extract, exception -> except)
    if w.endswith("tion") and len(w) > 5 and not w.endswith("ation"):
        return w[:-3]

    # Suffix -ing (e.g. parsing -> parse, validating -> validate, processing -> process)
    if w.endswith("ying") and len(w) > 5:
        return w[:-4] + "y"
    if w.endswith("ing") and len(w) > 4:
        base = w[:-3]
        if base.endswith("at") or base.endswith("iz") or base.endswith("id"):
            return base + "e"
        if len(base) >= 2 and base[-1] != "s" and base[-1] == base[-2]:
            return base[:-1]
        if base in ("pars", "clos", "mak", "writ"):
            return base + "e"
        return base

    # Suffix -ed (e.g. parsed -> parse, retried -> retry, validated -> validate)
    if w.endswith("ied") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if base.endswith("at") or base.endswith("iz") or base.endswith("id"):
            return base + "e"
        if len(base) >= 2 and base[-1] != "s" and base[-1] == base[-2]:
            return base[:-1]
        if base in ("pars", "clos", "mak", "writ"):
            return base + "e"
        return base

    # Suffix -er / -or (e.g. parser -> parse, validator -> validate, processor -> process)
    if w in ("parser", "validators", "validator", "processor", "miner", "compiler", "builder", "watcher"):
        agent_map = {
            "parser": "parse",
            "validator": "validate",
            "validators": "validate",
            "processor": "process",
            "miner": "mine",
            "compiler": "compile",
            "builder": "build",
            "watcher": "watch",
        }
        return agent_map.get(w, w)

    return w


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

    Supports:
    - snake_case (e.g. retry_payment -> RetryPayment, retryPayment, retry, payment)
    - CamelCase / PascalCase (e.g. PaymentProcessor -> payment_processor, payment, processor)
    - SCREAMING_SNAKE_CASE (e.g. MAX_RETRIES -> max_retries, maxRetries, max, retries)
    - kebab-case (e.g. retry-payment -> retry_payment, RetryPayment)
    - dot.notation (e.g. InvoiceParser.parse -> InvoiceParser, parse, invoice, parser)
    """
    variants: List[str] = [name]
    name_lower = name.lower()

    # kebab-case normalization
    if "-" in name:
        snake_name = name.replace("-", "_")
        variants.append(snake_name)
        name = snake_name

    # Dotted name decomposition
    if "." in name:
        dot_parts = name.split(".")
        for dp in dot_parts:
            variants.append(dp)
            variants.append(dp.lower())
            variants.extend(generate_identifier_variants(dp))

    # snake_case or SCREAMING_SNAKE_CASE
    if "_" in name:
        parts = _split_snake_case(name)
        if parts:
            pascal = "".join(p.capitalize() for p in parts)
            camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
            variants.append(pascal)
            variants.append(camel)
            variants.append(" ".join(parts))
            variants.append(name_lower)
            for p in parts:
                variants.append(p)
                variants.append(normalize_term_stem(p))
            # Suffixes of decreasing length
            for i in range(1, len(parts)):
                suffix_snake = "_".join(parts[i:])
                variants.append(suffix_snake)

    # CamelCase or PascalCase
    elif any(c.isupper() for c in name[1:]):
        parts = _split_camel_case(name)
        if parts:
            snake = "_".join(parts)
            variants.append(snake)
            variants.append(" ".join(parts))
            variants.append(name_lower)
            for p in parts:
                variants.append(p)
                variants.append(normalize_term_stem(p))
            for i in range(1, len(parts)):
                suffix_parts = parts[i:]
                variants.append("_".join(suffix_parts))
                variants.append(suffix_parts[0] + "".join(p.capitalize() for p in suffix_parts[1:]))
    else:
        variants.append(name_lower)
        stemmed = normalize_term_stem(name_lower)
        if stemmed != name_lower:
            variants.append(stemmed)

    # Deduplicate while preserving order (preserve casing variants)
    seen: Set[str] = set()
    unique: List[str] = []
    for v in variants:
        if v not in seen and len(v) > 1:
            seen.add(v)
            unique.append(v)
    return unique


def extract_task_identifiers(task: str) -> TaskIntent:
    """Extract structured identifiers, domain terms, compounds, and negative constraints from a task."""
    normalized = normalize_task_text(task)
    intent = TaskIntent(raw=task, normalized=normalized)

    # 1. Extract explicit negative exclusions (e.g. 'without modifying shipping', 'do not touch X')
    for m in _EXCLUSION_PATTERN.finditer(task):
        excl_target = m.group(1).strip()
        if excl_target and excl_target.lower() not in _STOP_WORDS:
            intent.exclusions.append(excl_target)

    # 2. Extract quoted code references (highest signal)
    for m in _QUOTED_RE.finditer(task):
        intent.quoted_names.append(m.group(1))

    # 3. Extract dotted names (e.g. PaymentService.retry, InvoiceParser.parse)
    for m in _DOTTED_NAME_RE.finditer(task):
        name = m.group()
        if "/" not in name and "\\" not in name:
            intent.dotted_names.append(name)

    # 4. Extract file paths
    for m in _PATH_RE.finditer(task):
        path = m.group()
        if "/" in path or "\\" in path or path.count(".") == 1:
            intent.paths.append(path)

    # 5. Extract API paths
    for m in _API_PATH_RE.finditer(task):
        intent.api_paths.append(m.group())

    # 6. Extract numeric values
    for m in _NUMBER_RE.finditer(task):
        intent.values.append(m.group())

    # 7. Tokenize for identifiers and concepts
    raw_tokens = re.findall(r"[A-Za-z_]\w*", normalized)
    content_tokens: List[str] = []

    for token in raw_tokens:
        token_lower = token.lower()
        if token_lower in _STOP_WORDS:
            continue

        # Pure operational verbs (e.g. 'modify', 'change')
        if token_lower in _OPERATIONAL_VERBS:
            intent.verbs.append(token_lower)
            continue

        # Technical verbs (e.g. 'validate', 'parse', 'test') are recorded as verbs AND concepts
        if token_lower in _TECHNICAL_VERBS:
            intent.verbs.append(token_lower)
            intent.concepts.append(token_lower)
            stemmed = normalize_term_stem(token_lower)
            intent.stemmed_concepts.append(stemmed)
            continue

        # CONSTANTS
        if _CONSTANT_RE.fullmatch(token):
            intent.identifiers.append(token)
            content_tokens.append(token_lower)
            continue

        # CamelCase, PascalCase, or mixedCase identifiers
        if any(c.isupper() for c in token[1:]):
            intent.identifiers.append(token)
            content_tokens.append(token_lower)
            continue

        # snake_case identifiers
        if "_" in token:
            intent.identifiers.append(token)
            content_tokens.append(token_lower)
            continue

        # General domain concepts (length > 2)
        if len(token_lower) > 2:
            intent.concepts.append(token_lower)
            stemmed = normalize_term_stem(token_lower)
            intent.stemmed_concepts.append(stemmed)
            content_tokens.append(token_lower)

    # 8. Generate domain compound variants from adjacent content tokens
    # e.g. ["payment", "retry"] -> "payment_retry", "retry_payment", "PaymentRetry"
    for i in range(len(content_tokens) - 1):
        t1, t2 = content_tokens[i], content_tokens[i + 1]
        s1, s2 = normalize_term_stem(t1), normalize_term_stem(t2)
        intent.compounds.extend([
            f"{t1}_{t2}",
            f"{t2}_{t1}",
            f"{s1}_{s2}",
            f"{s2}_{s1}",
            f"{t1.capitalize()}{t2.capitalize()}",
            f"{t2.capitalize()}{t1.capitalize()}",
            f"{t1}{t2.capitalize()}",
            f"{t2}{t1.capitalize()}",
        ])

    # Promote quoted and dotted names to identifiers
    for name in intent.quoted_names + intent.dotted_names:
        if name not in intent.identifiers:
            intent.identifiers.append(name)

    return intent


def _build_fts_query(intent: TaskIntent) -> str:
    """Build an SQLite FTS5 query string from extracted task identifiers and concepts."""
    terms: List[str] = []

    # 1. Exact identifiers, dotted names, quoted names
    for ident in intent.identifiers:
        if "." in ident:
            for part in ident.split("."):
                part_clean = re.sub(r"[^\w]", "", part)
                if part_clean and len(part_clean) > 1:
                    terms.append(part_clean)
        else:
            clean = re.sub(r"[^\w]", "", ident)
            if clean:
                terms.append(clean)
                for v in generate_identifier_variants(clean):
                    v_clean = re.sub(r"[^\w]", "", v)
                    if v_clean and len(v_clean) > 1:
                        terms.append(v_clean)

    # 2. Compound variants
    for comp in intent.compounds[:10]:
        clean = re.sub(r"[^\w]", "", comp)
        if clean and len(clean) > 2:
            terms.append(clean)

    # 3. Domain concepts and stems
    for concept in intent.concepts + intent.stemmed_concepts:
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

    return " OR ".join(unique_terms)


def _get_or_build_token_index(node_index: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Get or build an inverted token-to-nodeIds map cached on the node_index dict."""
    if "__token_inv_index__" in node_index:
        return node_index["__token_inv_index__"]

    inv: Dict[str, Set[str]] = defaultdict(set)
    for node_id, node_data in node_index.items():
        if node_id.startswith("__") or not isinstance(node_data, dict):
            continue

        nid_lower = node_id.lower()
        tokens = set(re.findall(r"[a-z0-9]+", nid_lower))

        # Split camelCase and PascalCase on raw node_id
        for m in re.finditer(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", node_id):
            w = m.group().lower()
            if len(w) > 1:
                tokens.add(w)

        # Exact suffix parts
        if "::" in nid_lower:
            tokens.add(nid_lower.split("::")[-1])
        if "." in nid_lower:
            tokens.add(nid_lower.split(".")[-1])

        # Signature
        sig = node_data.get("sig")
        if sig:
            tokens.update(re.findall(r"[a-z0-9]+", sig.lower()))

        # Story text
        story = node_data.get("story_text")
        if story:
            tokens.update(re.findall(r"[a-z0-9]+", story.lower()))

        for t in tokens:
            if len(t) > 1:
                inv[t].add(node_id)

    node_index["__token_inv_index__"] = inv
    return inv


def _ast_identifier_search(
    intent: TaskIntent,
    node_index: Dict[str, Any],
    limit: int = 50,
) -> List[Tuple[str, float]]:
    """Direct AST identifier matching against node IDs, signatures, and stories."""
    search_terms: List[str] = []
    for ident in intent.identifiers:
        search_terms.extend(generate_identifier_variants(ident))
    for comp in intent.compounds:
        search_terms.append(comp)
    for concept in intent.concepts:
        search_terms.append(concept)
        search_terms.append(normalize_term_stem(concept))

    search_terms_lower = {t.lower() for t in search_terms if len(t) > 1}
    if not search_terms_lower:
        return []

    inv = _get_or_build_token_index(node_index)

    candidate_node_ids: Set[str] = set()
    for term in search_terms_lower:
        if term in inv:
            candidate_node_ids.update(inv[term])

    # If no exact token match was found across inverted index, scan all nodes
    if not candidate_node_ids:
        candidate_node_ids = {nid for nid in node_index.keys() if not nid.startswith("__")}

    scored: Dict[str, float] = {}

    for node_id in candidate_node_ids:
        node_data = node_index.get(node_id)
        if not node_data or not isinstance(node_data, dict):
            continue

        node_id_lower = node_id.lower()
        sig_lower = (node_data.get("sig") or "").lower()
        story_lower = (node_data.get("story_text") or "").lower()
        kind = node_data.get("kind", "")

        score = 0.0
        for term in search_terms_lower:
            # Exact symbol ID suffix match (strongest signal)
            if node_id_lower.endswith(f"::{term}") or node_id_lower.endswith(f".{term}"):
                score += 10.0
            # Symbol name exact match after ::
            elif "::" in node_id_lower and node_id_lower.split("::")[-1] == term:
                score += 8.0
            # Word-boundary or snake segment match in ID
            elif f"_{term}" in node_id_lower or f"{term}_" in node_id_lower or f".{term}" in node_id_lower:
                score += 4.0
            elif len(term) > 3 and term in node_id_lower:
                score += 2.0

            # Signature match
            if term in sig_lower:
                score += 3.0
            # Story narrative match
            if term in story_lower:
                score += 1.0

        if score > 0:
            # Kind boost: prefer callable methods and functions over file cards
            if kind in ("function", "method", "class"):
                score *= 1.3
            elif kind in ("file", "module"):
                score *= 0.6
            scored[node_id] = score

    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return ranked[:limit]


def compute_retrieval_score(
    node_id: str,
    node_data: Dict[str, Any],
    intent: TaskIntent,
    bm25_rank_map: Dict[str, int],
) -> RetrievalScore:
    """Compute explicit, testable RetrievalScore component breakdown for a candidate symbol."""
    score = RetrievalScore()
    node_id_lower = node_id.lower()
    symbol_name = node_id.split("::")[-1] if "::" in node_id else node_id
    sym_lower = symbol_name.lower()
    sig_lower = (node_data.get("sig") or "").lower()
    story_lower = (node_data.get("story_text") or "").lower()
    file_lower = (node_data.get("file") or "").replace("\\", "/").lower()
    kind = node_data.get("kind", "")

    # 1. Exact Match Component [0..1]
    # Check exact match against explicit identifiers, dotted names, or compounds
    for target in intent.identifiers + intent.dotted_names + intent.quoted_names + intent.compounds:
        t_clean = target.strip().lower()
        if sym_lower == t_clean or node_id_lower.endswith(f"::{t_clean}"):
            score.exact_match = 1.0
            break
        elif "." in t_clean and sym_lower.endswith(t_clean.split(".")[-1]):
            score.exact_match = max(score.exact_match, 0.8)

    # 2. Identifier Match Component [0..1]
    sym_variants = set(generate_identifier_variants(symbol_name))
    sym_variants_lower = {v.lower() for v in sym_variants}

    id_match_points = 0.0
    query_targets = intent.identifiers + intent.concepts + intent.compounds
    for qt in query_targets:
        qt_lower = qt.lower()
        if qt_lower in sym_variants_lower:
            id_match_points += 1.0
        elif any(qt_lower in v for v in sym_variants_lower if len(qt_lower) > 3):
            id_match_points += 0.5

    if query_targets:
        score.identifier = min(1.0, id_match_points / max(1.0, len(intent.identifiers) or 1.0))

    # 3. Token Overlap Component [0..1]
    query_stems = set(intent.stemmed_concepts)
    for ident in intent.identifiers:
        for v in generate_identifier_variants(ident):
            query_stems.add(normalize_term_stem(v.lower()))

    # Build node token set
    node_tokens = set(re.findall(r"[A-Za-z0-9_]+", sym_lower + " " + sig_lower))
    node_stems = {normalize_term_stem(t) for t in node_tokens if len(t) > 1}

    if query_stems and node_stems:
        overlap = query_stems & node_stems
        score.token_overlap = min(1.0, len(overlap) / len(query_stems))

    # 4. Lexical BM25 Component [0..1]
    if node_id in bm25_rank_map:
        bm25_rank = bm25_rank_map[node_id]  # 0-indexed rank
        score.lexical = round(1.0 / (1.0 + 0.1 * bm25_rank), 4)

    # 5. Path Relevance Component [0..1]
    if intent.paths:
        for p in intent.paths:
            p_clean = p.replace("\\", "/").lower()
            if p_clean in file_lower or file_lower.endswith(p_clean):
                score.path_relevance = 1.0
                break
    else:
        # Check if file path contains concept words (e.g. 'billing' in 'src/billing/invoice.py')
        path_matches = sum(1 for c in intent.concepts if len(c) > 3 and c in file_lower)
        if path_matches > 0:
            score.path_relevance = min(1.0, 0.4 * path_matches)

    # 6. Kind Preference Component [0..1]
    if kind in ("function", "method", "class"):
        score.kind_preference = 1.0
    elif kind in ("sql_query", "json_config", "yaml_config"):
        score.kind_preference = 0.7
    elif kind in ("file", "module"):
        score.kind_preference = 0.3
    else:
        score.kind_preference = 0.2

    return score


def reciprocal_rank_fusion(
    *ranked_lists: List[Tuple[str, float]],
    k: int = 60,
    weights: Optional[List[float]] = None,
) -> List[Tuple[str, float]]:
    """Combine multiple ranked result lists using Reciprocal Rank Fusion.

    RRF(d) = sum_r  weight_r / (k + rank_r(d))
    """
    if not ranked_lists:
        return []

    if weights is None:
        weights = [1.0] * len(ranked_lists)

    fused_scores: Dict[str, float] = {}

    for retriever_idx, ranked in enumerate(ranked_lists):
        w = weights[retriever_idx] if retriever_idx < len(weights) else 1.0
        for rank_pos, (item_id, _original_score) in enumerate(ranked):
            rrf_contribution = w / (k + rank_pos + 1)
            fused_scores[item_id] = fused_scores.get(item_id, 0.0) + rrf_contribution

    return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)


def resolve_task_to_symbols(
    task: str,
    node_index: Dict[str, Any],
    fts_results: Optional[List[Tuple[str, float]]] = None,
    limit: int = 20,
    enable_stemming: bool = True,
    enable_compounds: bool = True,
    use_rrf_scoring: bool = False,
) -> List[SymbolCandidate]:
    """Resolve a natural language task to ranked candidate symbols.

    Enhanced PR20 Pipeline:
    1. Extract structured intent, stems, compounds, and negative constraints
    2. Candidate generation: AST identifier search (top 100) + FTS5 BM25 (top 100)
    3. Multi-component scoring (exact_match, identifier, token_overlap, lexical, path, kind)
    4. Deterministic ranking and SymbolCandidate generation with full score breakdown
    """
    intent = extract_task_identifiers(task)
    if not enable_stemming:
        intent.stemmed_concepts = []
    if not enable_compounds:
        intent.compounds = []

    # Stage 1: Broad Candidate Pool Generation (top 100 from each source)
    ast_candidates = _ast_identifier_search(intent, node_index, limit=100)
    fts_ranked = fts_results or []

    if use_rrf_scoring:
        # PR19 Baseline: Pure RRF ranking on AST and BM25 candidates
        fused = reciprocal_rank_fusion(ast_candidates, fts_ranked, k=60)
        candidates = []
        for nid, rrf_score in fused[:limit]:
            candidates.append(
                SymbolCandidate(
                    node_id=nid,
                    score=round(rrf_score, 4),
                    reasons=[{"type": "rrf", "score": rrf_score}],
                    breakdown={"rrf": rrf_score},
                )
            )
        return candidates

    # Map BM25 ranks
    bm25_rank_map: Dict[str, int] = {nid: rank for rank, (nid, _) in enumerate(fts_ranked)}

    # Combine candidates into pool
    candidate_pool_set: Set[str] = {nid for nid, _ in ast_candidates} | {nid for nid, _ in fts_ranked}
    if not candidate_pool_set:
        return []

    # Stage 2: Multi-Component Re-Ranking
    scored_candidates: List[Tuple[str, RetrievalScore]] = []
    for nid in candidate_pool_set:
        ndata = node_index.get(nid, {})
        r_score = compute_retrieval_score(nid, ndata, intent, bm25_rank_map)
        scored_candidates.append((nid, r_score))

    # Sort descending by calibrated total score
    scored_candidates.sort(key=lambda x: x[1].total, reverse=True)

    # Build SymbolCandidate instances
    candidates: List[SymbolCandidate] = []
    ast_ids = {nid for nid, _ in ast_candidates}
    fts_ids = set(bm25_rank_map.keys())

    for nid, r_score in scored_candidates[:limit]:
        reasons: List[Dict[str, Any]] = []

        if r_score.exact_match > 0:
            reasons.append({"type": "exact_match", "score": r_score.exact_match})
        if r_score.identifier > 0:
            reasons.append({"type": "identifier_match", "score": r_score.identifier})
        if r_score.token_overlap > 0:
            reasons.append({"type": "token_overlap", "score": r_score.token_overlap})
        if nid in fts_ids:
            reasons.append({"type": "bm25", "score": r_score.lexical})

        candidates.append(
            SymbolCandidate(
                node_id=nid,
                score=r_score.total,
                reasons=reasons,
                breakdown=r_score.to_dict(),
            )
        )

    return candidates


def explain_task(
    task: str,
    node_index: Dict[str, Any],
    fts_results: Optional[List[Tuple[str, float]]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """Provide transparent, deterministic explainability for task retrieval decisions."""
    intent = extract_task_identifiers(task)
    candidates = resolve_task_to_symbols(task, node_index, fts_results=fts_results, limit=limit)

    return {
        "original_task": task,
        "normalized_task": intent.normalized,
        "extracted_identifiers": intent.identifiers,
        "extracted_concepts": intent.concepts,
        "stemmed_concepts": intent.stemmed_concepts,
        "compounds": intent.compounds[:10],
        "exclusions": intent.exclusions,
        "candidate_scores": [
            {
                "node_id": c.node_id,
                "total_score": c.score,
                "breakdown": c.breakdown,
                "reasons": c.reasons,
            }
            for c in candidates
        ],
        "selected_entrypoints": [c.node_id for c in candidates[:3]],
    }


def format_explain(explanation: Dict[str, Any]) -> str:
    """Format explanation dictionary into human-readable text block."""
    lines = [
        "QUERY",
        "-----",
        f"original:   \"{explanation.get('original_task')}\"",
        f"normalized: {explanation.get('normalized_task')}",
        "",
        f"identifiers: {', '.join(explanation.get('extracted_identifiers', [])) or '(none)'}",
        f"concepts:    {', '.join(explanation.get('stemmed_concepts', [])) or '(none)'}",
        f"compounds:   {', '.join(explanation.get('compounds', [])[:6]) or '(none)'}",
    ]
    if explanation.get("exclusions"):
        lines.append(f"exclusions:  {', '.join(explanation.get('exclusions'))}")

    lines.extend([
        "",
        "CANDIDATES",
        "----------",
    ])

    for idx, c in enumerate(explanation.get("candidate_scores", []), 1):
        bd = c.get("breakdown") or {}
        lines.extend([
            f"{idx}. {c.get('node_id')}",
            f"   total_score:    {c.get('total_score', 0.0):.4f}",
            f"   exact_match:    {bd.get('exact_match', 0.0):.2f}",
            f"   identifier:     {bd.get('identifier', 0.0):.2f}",
            f"   token_overlap:  {bd.get('token_overlap', 0.0):.2f}",
            f"   lexical_bm25:   {bd.get('lexical', 0.0):.2f}",
            f"   path_relevance: {bd.get('path_relevance', 0.0):.2f}",
            f"   kind_pref:      {bd.get('kind_preference', 0.0):.2f}",
            "",
        ])

    lines.extend([
        "SELECTED ENTRYPOINTS",
        "--------------------",
    ])
    for ep in explanation.get("selected_entrypoints", []):
        lines.append(f"-> {ep}")

    return "\n".join(lines).strip()
