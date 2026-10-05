"""Git commit history miner and temporal co-change matrix for RepoPeek."""

from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import time
from typing import Dict, List, Optional, Set, Tuple

from repopeek.models.schema import CanonicalGraph, Confidence, Edge, EdgeType, Evidence, NodeCard


@dataclass
class CommitRecord:
    """Parsed commit record from git history."""
    commit_hash: str
    timestamp: float
    files: List[str]


@dataclass
class CoChangeRelation:
    """Pairwise co-change statistical relationship."""
    file_a: str
    file_b: str
    probability: float  # P(B|A)
    co_commit_count: int
    total_commits_a: int
    last_co_commit_age_days: float


class GitTemporalMiner:
    """Mines git commit history, computes exponential time decay, and builds co-change graph edges."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        half_life_days: float = 180.0,
        min_confidence: float = 0.25,
        min_commits: int = 2,
        max_files_per_commit: int = 50,
    ) -> None:
        self.repo_root = Path(repo_root or ".").resolve()
        self.half_life_days = half_life_days
        self.min_confidence = min_confidence
        self.min_commits = min_commits
        self.max_files_per_commit = max_files_per_commit
        self.decay_constant = math.log(2) / max(1.0, self.half_life_days)

    def mine_commits(self, max_commits: int = 2000) -> List[CommitRecord]:
        """Extract commit history via git log without merges."""
        if not (self.repo_root / ".git").exists():
            return []

        try:
            cmd = [
                "git",
                "log",
                "--no-merges",
                "--name-only",
                f"--format=COMMIT:%H|%at",
                f"-n{max_commits}",
            ]
            res = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if res.returncode != 0:
                return []
            return self._parse_git_log(res.stdout)
        except Exception:
            return []

    def _parse_git_log(self, raw_log: str) -> List[CommitRecord]:
        """Parse raw git log stdout into CommitRecords."""
        records: List[CommitRecord] = []
        curr_hash: Optional[str] = None
        curr_ts: float = 0.0
        curr_files: List[str] = []

        for line in raw_log.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("COMMIT:"):
                if curr_hash and curr_files:
                    records.append(
                        CommitRecord(
                            commit_hash=curr_hash,
                            timestamp=curr_ts,
                            files=curr_files,
                        )
                    )
                parts = line[7:].split("|")
                curr_hash = parts[0]
                curr_ts = float(parts[1]) if len(parts) > 1 and parts[1].isdigit() else time.time()
                curr_files = []
            else:
                norm_file = Path(line).as_posix().lstrip("./")
                curr_files.append(norm_file)

        if curr_hash and curr_files:
            records.append(
                CommitRecord(
                    commit_hash=curr_hash,
                    timestamp=curr_ts,
                    files=curr_files,
                )
            )

        return records

    def compute_co_changes(
        self,
        commits: Optional[List[CommitRecord]] = None,
        reference_time: Optional[float] = None,
    ) -> List[CoChangeRelation]:
        """Compute pairwise co-change probabilities P(B|A) with exponential temporal decay."""
        if commits is None:
            commits = self.mine_commits()
        if not commits:
            return []

        if reference_time is None:
            reference_time = max(c.timestamp for c in commits)

        file_weight: Dict[str, float] = defaultdict(float)
        file_count: Dict[str, int] = defaultdict(int)
        pair_weight: Dict[Tuple[str, str], float] = defaultdict(float)
        pair_count: Dict[Tuple[str, str], int] = defaultdict(int)
        pair_last_ts: Dict[Tuple[str, str], float] = {}

        for c in commits:
            if len(c.files) > self.max_files_per_commit or len(c.files) < 2:
                continue

            age_days = max(0.0, (reference_time - c.timestamp) / 86400.0)
            weight = math.exp(-self.decay_constant * age_days)

            unique_files = sorted(set(c.files))
            for f in unique_files:
                file_weight[f] += weight
                file_count[f] += 1

            for i in range(len(unique_files)):
                f_a = unique_files[i]
                for j in range(len(unique_files)):
                    if i == j:
                        continue
                    f_b = unique_files[j]
                    pair_weight[(f_a, f_b)] += weight
                    pair_count[(f_a, f_b)] += 1
                    if (f_a, f_b) not in pair_last_ts or c.timestamp > pair_last_ts[(f_a, f_b)]:
                        pair_last_ts[(f_a, f_b)] = c.timestamp

        relations: List[CoChangeRelation] = []
        for (f_a, f_b), p_wt in pair_weight.items():
            tot_a_wt = file_weight.get(f_a, 0.0)
            count = pair_count[(f_a, f_b)]
            if tot_a_wt <= 0.0 or count < self.min_commits:
                continue

            prob = min(0.99, p_wt / tot_a_wt)
            if prob >= self.min_confidence:
                last_age = max(0.0, (reference_time - pair_last_ts[(f_a, f_b)]) / 86400.0)
                relations.append(
                    CoChangeRelation(
                        file_a=f_a,
                        file_b=f_b,
                        probability=round(prob, 4),
                        co_commit_count=count,
                        total_commits_a=file_count[f_a],
                        last_co_commit_age_days=round(last_age, 1),
                    )
                )

        relations.sort(key=lambda r: (r.probability, r.co_commit_count), reverse=True)
        return relations

    def build_graph_edges(
        self,
        graph: CanonicalGraph,
        relations: Optional[List[CoChangeRelation]] = None,
    ) -> List[Edge]:
        """Generate CO_CHANGED_WITH edges between existing file/module nodes in graph."""
        if relations is None:
            relations = self.compute_co_changes()

        file_node_map: Dict[str, str] = {}
        for nid, node in graph.nodes.items():
            if node.kind in ("file", "module") and node.span:
                file_node_map[node.span.file] = nid

        edges: List[Edge] = []
        for rel in relations:
            src_nid = file_node_map.get(rel.file_a)
            dst_nid = file_node_map.get(rel.file_b)
            if src_nid and dst_nid and src_nid != dst_nid:
                edges.append(
                    Edge(
                        src=src_nid,
                        dst=dst_nid,
                        type=EdgeType.CO_CHANGED_WITH,
                        confidence=Confidence.RESOLVED,
                        evidence=Evidence(
                            file=rel.file_a,
                            start_line=1,
                            end_line=1,
                            how_derived=f"git_cochange(P={rel.probability:.2f},count={rel.co_commit_count})",
                        ),
                    )
                )
        return edges
