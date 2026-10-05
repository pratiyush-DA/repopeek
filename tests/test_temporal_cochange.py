"""Unit tests for Git Temporal Intelligence and Co-Change Matrix."""

import json
import math
from pathlib import Path
import pytest

from repopeek.cli import main
from repopeek.models.schema import CanonicalGraph, EdgeType, NodeCard, Span
from repopeek.query.engine import GraphQueryEngine
from repopeek.temporal.miner import CommitRecord, GitTemporalMiner


def test_parse_git_log():
    raw_log = """COMMIT:abc1234|1700000000
src/billing/invoice.py
src/models/account.py

COMMIT:def5678|1705000000
src/billing/invoice.py
src/utils/tax.py
src/models/account.py
"""
    miner = GitTemporalMiner()
    commits = miner._parse_git_log(raw_log)

    assert len(commits) == 2
    assert commits[0].commit_hash == "abc1234"
    assert commits[0].timestamp == 1700000000.0
    assert set(commits[0].files) == {"src/billing/invoice.py", "src/models/account.py"}

    assert commits[1].commit_hash == "def5678"
    assert commits[1].timestamp == 1705000000.0
    assert len(commits[1].files) == 3


def test_temporal_weight_decay():
    half_life = 180.0
    miner = GitTemporalMiner(half_life_days=half_life)

    ref_time = 1000000.0
    day = 86400.0

    # Commit at ref_time (age 0)
    c0 = CommitRecord(commit_hash="c0", timestamp=ref_time, files=["a.py", "b.py"])
    # Commit at ref_time - 180 days (age 180)
    c1 = CommitRecord(commit_hash="c1", timestamp=ref_time - 180 * day, files=["a.py", "b.py"])
    # Commit at ref_time - 360 days (age 360)
    c2 = CommitRecord(commit_hash="c2", timestamp=ref_time - 360 * day, files=["a.py", "b.py"])

    # Age 0 weight = 1.0
    # Age 180 weight = 0.5
    # Age 360 weight = 0.25
    decay_constant = math.log(2) / half_life
    w0 = math.exp(-decay_constant * 0)
    w1 = math.exp(-decay_constant * 180)
    w2 = math.exp(-decay_constant * 360)

    assert pytest.approx(w0, 0.001) == 1.0
    assert pytest.approx(w1, 0.001) == 0.5
    assert pytest.approx(w2, 0.001) == 0.25


def test_compute_co_changes():
    ref_time = 1000000.0
    day = 86400.0

    # File A is modified in 3 commits:
    # 1. c0 (today): A and B
    # 2. c1 (180 days ago): A and B
    # 3. c2 (today): A and C
    commits = [
        CommitRecord("c0", ref_time, ["src/a.py", "src/b.py"]),
        CommitRecord("c1", ref_time - 180 * day, ["src/a.py", "src/b.py"]),
        CommitRecord("c2", ref_time, ["src/a.py", "src/c.py"]),
    ]

    miner = GitTemporalMiner(half_life_days=180.0, min_confidence=0.20, min_commits=1)
    relations = miner.compute_co_changes(commits, reference_time=ref_time)

    # Total weight of A = 1.0 (c0) + 0.5 (c1) + 1.0 (c2) = 2.5
    # Weight of (A, B) = 1.0 + 0.5 = 1.5
    # P(B|A) = 1.5 / 2.5 = 0.60
    rel_ab = next(r for r in relations if r.file_a == "src/a.py" and r.file_b == "src/b.py")
    assert pytest.approx(rel_ab.probability, 0.01) == 0.60
    assert rel_ab.co_commit_count == 2
    assert rel_ab.total_commits_a == 3

    # Weight of (A, C) = 1.0
    # P(C|A) = 1.0 / 2.5 = 0.40
    rel_ac = next(r for r in relations if r.file_a == "src/a.py" and r.file_b == "src/c.py")
    assert pytest.approx(rel_ac.probability, 0.01) == 0.40
    assert rel_ac.co_commit_count == 1


def test_build_graph_edges():
    graph = CanonicalGraph()
    card_a = NodeCard(
        id="py:src/a.py::<module>",
        kind="file",
        sig="module src/a.py",
        span=Span(file="src/a.py", start=1, end=10),
        content_hash="hash_a",
    )
    card_b = NodeCard(
        id="py:src/b.py::<module>",
        kind="file",
        sig="module src/b.py",
        span=Span(file="src/b.py", start=1, end=10),
        content_hash="hash_b",
    )
    graph.add_node(card_a)
    graph.add_node(card_b)

    commits = [
        CommitRecord("c1", 1000.0, ["src/a.py", "src/b.py"]),
        CommitRecord("c2", 2000.0, ["src/a.py", "src/b.py"]),
    ]

    miner = GitTemporalMiner(min_confidence=0.50, min_commits=2)
    relations = miner.compute_co_changes(commits, reference_time=2000.0)
    edges = miner.build_graph_edges(graph, relations)

    assert len(edges) == 2  # A->B and B->A
    ab_edge = next(e for e in edges if e.src == card_a.id and e.dst == card_b.id)
    assert ab_edge.type == EdgeType.CO_CHANGED_WITH
    assert "git_cochange" in ab_edge.evidence.how_derived


def test_query_engine_co_changes(monkeypatch):
    graph = CanonicalGraph()
    card_a = NodeCard(
        id="py:src/service.py::<module>",
        kind="file",
        sig="module src/service.py",
        span=Span(file="src/service.py", start=1, end=50),
        content_hash="hash_service",
    )
    graph.add_node(card_a)

    engine = GraphQueryEngine(graph=graph)

    # Mock mine_commits on GitTemporalMiner
    def mock_mine(self, max_commits=2000):
        return [
            CommitRecord("c1", 1000.0, ["src/service.py", "src/db.py"]),
            CommitRecord("c2", 2000.0, ["src/service.py", "src/db.py"]),
        ]

    monkeypatch.setattr(GitTemporalMiner, "mine_commits", mock_mine)

    results = engine.co_changes("src/service.py")
    assert len(results) >= 1
    res = results[0]
    assert res["target_file"] == "src/service.py"
    assert res["co_changed_file"] == "src/db.py"
    assert pytest.approx(res["probability"], 0.01) == 0.99


def test_cli_co_changes_flag(capsys, monkeypatch):
    def mock_mine(self, max_commits=2000):
        return [
            CommitRecord("c1", 1000.0, ["src/service.py", "src/db.py"]),
            CommitRecord("c2", 2000.0, ["src/service.py", "src/db.py"]),
        ]

    monkeypatch.setattr(GitTemporalMiner, "mine_commits", mock_mine)

    code = main(["--co-changes", "src/service.py", "--repo-path", "."])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["co_changed_file"] == "src/db.py"
