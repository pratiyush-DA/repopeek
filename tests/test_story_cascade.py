"""Tests for 5-tier story generation cascade, content-hash cache, fact verifier, and cost governor."""

import json
from pathlib import Path
import pytest

from repopeek.enrichment import (
    CostGovernor,
    DeterministicStoryBuilder,
    FactVerifier,
    HierarchicalStoryGenerator,
    StoryCache,
    StoryPipeline,
)
from repopeek.graph.builder import GraphBuilder
from repopeek.llm import MockProvider, ModelTier
from repopeek.models.schema import (
    CanonicalGraph,
    NodeCard,
    NodeFacts,
    NodeStory,
    Span,
)


def _make_dummy_node(
    node_id: str = "python:calc.py::add",
    kind: str = "function",
    complexity: int = 1,
    calls: int = 0,
    reads: list = None,
    writes: list = None,
    params: list = None,
    returns: str = "int",
) -> NodeCard:
    """Helper creating a test NodeCard."""
    return NodeCard(
        id=node_id,
        kind=kind,
        sig="def add(a: int, b: int) -> int",
        span=Span(file="calc.py", start=1, end=5),
        facts=NodeFacts(
            calls=calls,
            reads=reads or [],
            writes=writes or [],
            params=params or ["a", "b"],
            returns=returns,
            complexity=complexity,
        ),
        content_hash=f"hash_{node_id}",
    )


def test_story_cache_operations(tmp_path: Path):
    """Verify cache get, put, hit/miss tracking, and JSON disk persistence."""
    cache_file = tmp_path / "story_cache.json"
    cache = StoryCache(cache_file=cache_file)

    key = cache.make_key("content_hash_1", "fast")
    assert cache.get(key) is None
    assert cache.misses == 1

    story = NodeStory(text="Computes sum", source="llm", confidence="high")
    cache.put(key, story)

    cached_story = cache.get(key)
    assert cached_story is not None
    assert cached_story.text == "Computes sum"
    assert cached_story.source == "cached"
    assert cache.hits == 1

    # Persist and reload
    cache.save()
    assert cache_file.exists()

    reloaded_cache = StoryCache(cache_file=cache_file)
    reloaded_story = reloaded_cache.get(key)
    assert reloaded_story is not None
    assert reloaded_story.text == "Computes sum"


def test_fact_verifier_hallucination_detection():
    """Verify FactVerifier catches empty text, code dumps, and hallucinated table references."""
    verifier = FactVerifier()
    node = _make_dummy_node(
        node_id="py:billing.py::parse",
        reads=["sql:db/queries.sql::table.invoices"],
    )

    # 1. Valid grounded story
    v_valid = verifier.verify(node, "Parses invoice records from table.invoices and returns total")
    assert v_valid.is_valid is True

    # 2. Empty story
    v_empty = verifier.verify(node, "   ")
    assert v_empty.is_valid is False
    assert "empty" in v_empty.issues[0].lower()

    # 3. Excessive length (> 60 words)
    long_text = " ".join(["word"] * 65)
    v_long = verifier.verify(node, long_text)
    assert v_long.is_valid is False
    assert "maximum word count" in v_long.issues[0]

    # 4. Raw code block
    v_code = verifier.verify(node, "```python\ndef parse(): pass\n```")
    assert v_code.is_valid is False
    assert "raw code" in v_code.issues[0]

    # 5. Hallucinated table reference (mentions table users when node reads invoices)
    v_hallucinated = verifier.verify(node, "Fetches customer profiles from table users and computes total")
    assert v_hallucinated.is_valid is False
    assert any("Hallucinated table" in iss for iss in v_hallucinated.issues)

    # 6. Zero calls node claiming external service call
    zero_calls_node = _make_dummy_node(calls=0)
    v_calls = verifier.verify(zero_calls_node, "Sends HTTP request to external service API")
    assert v_calls.is_valid is False


def test_cost_governor_budget_enforcement():
    """Verify CostGovernor halts LLM requests upon token or dollar exhaustion."""
    governor = CostGovernor(max_tokens=1000, max_cost_usd=0.01, dry_run=False)

    assert governor.can_call_llm(estimated_tokens=200) is True

    # Simulate usage
    governor.record_usage(prompt_tokens=500, completion_tokens=200, cached_tokens=100, model="qwen/qwen3.8-27b")
    assert governor.total_tokens == 700
    assert governor.estimated_cost_usd > 0
    assert governor.can_call_llm(estimated_tokens=400) is False  # 700 + 400 > 1000

    # Dry run check
    dry_gov = CostGovernor(dry_run=True)
    assert dry_gov.can_call_llm() is False

    summary = governor.get_summary()
    assert summary["llm_calls"] == 1
    assert summary["total_tokens"] == 700


def test_deterministic_story_builder():
    """Verify DeterministicStoryBuilder handles functions, tables, and scripts without LLM."""
    # Function with reads and writes
    fn_node = _make_dummy_node(
        node_id="python:billing.py::update_invoice",
        reads=["table.invoices"],
        writes=["table.audit_log"],
    )
    fn_story = DeterministicStoryBuilder.build_story(fn_node)
    assert fn_story.source == "deterministic"
    assert "invoices" in fn_story.text
    assert "audit_log" in fn_story.text

    # Table node
    tbl_node = NodeCard(
        id="sql:db.sql::table.users",
        kind="sql_table",
        content_hash="hash_tbl",
    )
    tbl_story = DeterministicStoryBuilder.build_story(tbl_node)
    assert "Relational table 'users'" in tbl_story.text

    # Shell script node
    sh_node = NodeCard(
        id="sh:scripts/run.sh::run.sh",
        kind="shell_script",
        content_hash="hash_sh",
    )
    sh_story = DeterministicStoryBuilder.build_story(sh_node)
    assert "Shell script" in sh_story.text


def test_hierarchical_story_generator_cascade():
    """Verify the 5-tier cascade: trivial bypass, caching, LLM invocation, verifier downgrade, and strong tier."""
    provider = MockProvider()
    cache = StoryCache()
    governor = CostGovernor()
    generator = HierarchicalStoryGenerator(provider=provider, cache=cache, governor=governor)

    # 1. Tier 1: Trivial node (complexity 1, no calls, no reads/writes)
    trivial_node = _make_dummy_node(complexity=1, calls=0, reads=[], writes=[])
    story1 = generator.generate_story(trivial_node)
    assert story1.source == "deterministic"
    assert len(provider.history) == 0  # Zero LLM calls

    # 2. Tier 3: Non-trivial leaf node invokes fast tier
    complex_node = _make_dummy_node(
        node_id="python:calc.py::complex_calc",
        complexity=3,
        calls=2,
        reads=["table.invoices"],
    )
    story2 = generator.generate_story(complex_node)
    assert story2.source == "llm"
    assert len(provider.history) == 1
    assert provider.history[0].tier == ModelTier.FAST

    # 3. Tier 2: Re-requesting the same node hits content-hash cache
    story3 = generator.generate_story(complex_node)
    assert story3.source == "cached"
    assert len(provider.history) == 1  # Still 1 LLM call

    # 4. Tier 5: High complexity hotspot escalates to strong tier
    hotspot_node = _make_dummy_node(
        node_id="python:calc.py::super_engine",
        complexity=12,
        calls=10,
    )
    story4 = generator.generate_story(hotspot_node)
    assert len(provider.history) == 2
    assert provider.history[1].tier == ModelTier.STRONG

    # 5. Anti-hallucination verification downgrade
    hallucinating_provider = MockProvider(
        canned_response=json.dumps({"summary": "Reads table customer_orders and updates payments"})
    )
    generator_with_bad_llm = HierarchicalStoryGenerator(
        provider=hallucinating_provider,
        cache=StoryCache(),
    )
    clean_node = _make_dummy_node(
        node_id="python:calc.py::pure_math",
        complexity=2,
        calls=1,
        reads=[],
        writes=[],
    )
    story5 = generator_with_bad_llm.generate_story(clean_node)
    # The verifier catches 'table customer_orders' as a hallucination and downgrades to deterministic
    assert story5.source == "deterministic"
    assert story5.confidence == "medium"


def test_story_pipeline_end_to_end_on_sample_repo():
    """Verify full graph bottom-up enrichment pipeline on sample repository fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_repo"
    builder = GraphBuilder()
    graph = builder.build_from_directory(fixture_path)

    provider = MockProvider()
    pipeline = StoryPipeline(provider=provider)
    report = pipeline.enrich(graph)

    assert report.total_nodes == len(graph.nodes)
    assert report.stories_generated == len(graph.nodes)
    assert (report.deterministic_stories + report.llm_stories + report.cached_hits) == report.total_nodes

    # All nodes must have a story attached
    for node in graph.nodes.values():
        assert node.story is not None
        assert node.story.text
        assert node.story.source in ("deterministic", "llm", "cached")
