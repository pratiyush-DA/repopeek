"""Content-hash based story cache for zero-redundancy incremental summarization."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from repopeek.discovery.hasher import hash_content
from repopeek.models.schema import NodeStory


class StoryCache:
    """Persistent content-hash cache preventing re-summarization of unchanged code."""

    def __init__(self, cache_file: Optional[Path] = None) -> None:
        self.cache_file = Path(cache_file).resolve() if cache_file else None
        self._entries: Dict[str, Dict[str, Any]] = {}
        self.hits: int = 0
        self.misses: int = 0
        if self.cache_file and self.cache_file.exists():
            self.load()

    @staticmethod
    def make_key(content_hash: str, model_tier: str, prompt_version: str = "v1") -> str:
        """Derive a stable cache key combining content signature, tier, and prompt schema."""
        raw = f"{content_hash}:{model_tier}:{prompt_version}"
        return hash_content(raw)

    def get(self, key: str) -> Optional[NodeStory]:
        """Retrieve cached story if key exists, returning story with source='cached'."""
        if key in self._entries:
            self.hits += 1
            entry = self._entries[key]
            return NodeStory(
                text=entry["text"],
                source="cached",
                confidence=entry.get("confidence", "high"),
            )
        self.misses += 1
        return None

    def put(self, key: str, story: NodeStory) -> None:
        """Store story record indexed by stable key."""
        self._entries[key] = {
            "text": story.text,
            "source": story.source,
            "confidence": story.confidence,
        }

    def load(self) -> None:
        """Load cache entries from JSON file."""
        if not self.cache_file or not self.cache_file.exists():
            return
        try:
            raw = self.cache_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                self._entries = data.get("entries", {})
        except (json.JSONDecodeError, OSError):
            self._entries = {}

    def save(self) -> None:
        """Persist cache entries to disk safely."""
        if not self.cache_file:
            return
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0.0",
            "entries_count": len(self._entries),
            "entries": self._entries,
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        self.cache_file.write_text(serialized, encoding="utf-8")

    @property
    def stats(self) -> Dict[str, Any]:
        """Return cache hit/miss diagnostic metrics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "entries": len(self._entries),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
        }
