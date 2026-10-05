"""Incremental file watching and background sync daemon for RepoPeek.

Monitors repository changes in real-time and incrementally syncs the code property
graph, storage shards, and SQLite search/traversal indices in <50ms without full rebuilds.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from repopeek.discovery.classifier import classify_file, SUPPORTED_TYPES
from repopeek.discovery.crawler import discover_repository
from repopeek.graph.builder import GraphBuilder
from repopeek.models.schema import CanonicalGraph
from repopeek.storage import update_file_shard, update_sqlite_file
from repopeek.storage.json_store import load_canonical_graph

logger = logging.getLogger("repopeek.daemon")


@dataclass
class FileState:
    """Tracked filesystem state of a repository source file."""
    mtime_ns: int
    size_bytes: int


class RepoPeekWatcher:
    """Stdlib-based resilient file watcher and incremental graph synchronizer."""

    def __init__(
        self,
        repo_root: Path,
        output_dir: Path,
        graph: Optional[CanonicalGraph] = None,
        poll_interval: float = 1.0,
        debounce_ms: int = 150,
        on_change: Optional[Callable[[Path, CanonicalGraph], None]] = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.poll_interval = max(0.1, poll_interval)
        self.debounce_sec = max(0.0, debounce_ms / 1000.0)
        self.on_change = on_change
        self.builder = GraphBuilder()

        # Load or initialize graph
        if graph is not None:
            self.graph = graph
        else:
            try:
                self.graph = load_canonical_graph(self.output_dir)
            except Exception:
                self.graph = self.builder.build_from_directory(self.repo_root)

        # Baseline file snapshot: rel_path -> FileState
        self._file_states: Dict[str, FileState] = {}
        self._initialize_snapshot()

    def _is_supported_source(self, path: Path) -> bool:
        """Return True if the file matches supported parsable extensions."""
        ft = classify_file(path)
        return ft in SUPPORTED_TYPES

    def _initialize_snapshot(self) -> None:
        """Scan target repository to record initial baseline modification timestamps."""
        files = discover_repository(self.repo_root)
        for f in files:
            if self._is_supported_source(f.path) and f.path.exists():
                try:
                    rel_p = str(f.path.relative_to(self.repo_root)).replace("\\", "/")
                    st = f.path.stat()
                    self._file_states[rel_p] = FileState(mtime_ns=st.st_mtime_ns, size_bytes=st.st_size)
                except Exception:
                    pass

    def scan_changes(self) -> List[Path]:
        """Detect modified, added, or deleted source files since last snapshot."""
        changed: List[Path] = []
        current_seen: Set[str] = set()

        files = discover_repository(self.repo_root)
        for f in files:
            if not self._is_supported_source(f.path) or not f.path.exists():
                continue

            try:
                rel_p = str(f.path.relative_to(self.repo_root)).replace("\\", "/")
                current_seen.add(rel_p)
                st = f.path.stat()
                prev = self._file_states.get(rel_p)

                if prev is None or st.st_mtime_ns > prev.mtime_ns or st.st_size != prev.size_bytes:
                    changed.append(f.path)
                    self._file_states[rel_p] = FileState(mtime_ns=st.st_mtime_ns, size_bytes=st.st_size)
            except Exception:
                continue

        # Check for deleted files
        deleted_keys = set(self._file_states.keys()) - current_seen
        for del_p in deleted_keys:
            del self._file_states[del_p]
            # When a file is deleted, remove its nodes from graph
            old_ids = [
                nid for nid, node in self.graph.nodes.items()
                if node.span and node.span.file == del_p
            ]
            for nid in old_ids:
                self.graph.nodes.pop(nid, None)
            self.graph.edges = [
                e for e in self.graph.edges
                if e.src not in old_ids and e.dst not in old_ids
            ]
            self.graph.dirty = True

        return changed

    def sync_file(self, file_path: Path) -> float:
        """Incrementally update graph, shard, and SQLite index for a single file in <50ms.

        Returns:
            Elapsed time in milliseconds.
        """
        start_t = time.perf_counter()
        target = file_path.resolve()
        if not target.exists():
            return 0.0

        try:
            rel_p = str(target.relative_to(self.repo_root)).replace("\\", "/")
        except ValueError:
            rel_p = target.as_posix()

        # 1. Update in-memory graph
        self.builder.update_file(target, self.graph, repo_root=self.repo_root)

        # 2. Update storage shard & manifest
        update_file_shard(self.output_dir, rel_p, self.graph)

        # 3. Update SQLite cache if active
        db_path = self.output_dir / "cache.db"
        if db_path.exists():
            update_sqlite_file(rel_p, self.graph, db_path)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        if self.on_change:
            try:
                self.on_change(target, self.graph)
            except Exception as e:
                logger.warning(f"Error in on_change callback: {e}")

        return elapsed_ms

    def run_once(self) -> List[Tuple[Path, float]]:
        """Run single sync sweep. Returns list of (changed_file, elapsed_ms)."""
        changed_files = self.scan_changes()
        results: List[Tuple[Path, float]] = []

        if changed_files and self.debounce_sec > 0:
            time.sleep(self.debounce_sec)

        for f in changed_files:
            elapsed = self.sync_file(f)
            results.append((f, elapsed))

        return results

    def run(self, max_iterations: Optional[int] = None) -> None:
        """Execute watch daemon polling loop until interrupted or max_iterations reached."""
        logger.info(f"RepoPeek watch daemon active on '{self.repo_root}' (poll interval: {self.poll_interval}s)")
        print(f"RepoPeek watch daemon active on '{self.repo_root}'. Press Ctrl+C to stop.")

        iterations = 0
        try:
            while max_iterations is None or iterations < max_iterations:
                changes = self.run_once()
                for changed_path, elapsed_ms in changes:
                    try:
                        rel_p = changed_path.relative_to(self.repo_root).as_posix()
                    except ValueError:
                        rel_p = changed_path.name
                    print(f"[{time.strftime('%H:%M:%S')}] Incremental sync '{rel_p}' in {elapsed_ms:.1f}ms (Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)})")

                iterations += 1
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nWatch daemon stopped.")
            logger.info("Watch daemon stopped by user.")
