"""Benchmark dataset parser, validator, and loader supporting YAML and JSON."""

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union
import yaml

from repopeek.evaluation.models import BenchmarkTask, GoldReference


class BenchmarkDataset:
    """A collection of benchmark evaluation tasks."""

    def __init__(self, tasks: Optional[List[BenchmarkTask]] = None, version: str = "v1") -> None:
        self.tasks: List[BenchmarkTask] = tasks or []
        self.version = version

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self) -> Iterator[BenchmarkTask]:
        return iter(self.tasks)

    def __getitem__(self, idx: Union[int, str]) -> BenchmarkTask:
        if isinstance(idx, int):
            return self.tasks[idx]
        task = self.get_task(idx)
        if task is None:
            raise KeyError(f"Task with ID '{idx}' not found in benchmark dataset.")
        return task

    def get_task(self, task_id: str) -> Optional[BenchmarkTask]:
        """Lookup task by its unique ID."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def filter_by_category(self, category_prefix: str) -> List[BenchmarkTask]:
        """Filter tasks by category name or prefix."""
        pref = category_prefix.lower()
        return [t for t in self.tasks if pref in t.category.lower()]

    @property
    def categories(self) -> List[str]:
        """List distinct categories in the dataset in sorted order."""
        return sorted(list({t.category for t in self.tasks}))

    def validate(self) -> List[str]:
        """Validate integrity and schema conformity of tasks.

        Returns list of validation error messages (empty if valid).
        """
        errors: List[str] = []
        seen_ids = set()

        for idx, t in enumerate(self.tasks):
            if not t.id or not isinstance(t.id, str):
                errors.append(f"Task at index {idx} has invalid or missing ID.")
            elif t.id in seen_ids:
                errors.append(f"Duplicate task ID '{t.id}' found at index {idx}.")
            else:
                seen_ids.add(t.id)

            if not t.task or not t.task.strip():
                errors.append(f"Task '{t.id}' has empty task description.")

            if not t.gold.symbols and not t.gold.files and not t.gold.excluded:
                errors.append(f"Task '{t.id}' has no gold symbols, files, or exclusions defined.")

        return errors

    @classmethod
    def load_file(cls, path: Union[Path, str]) -> "BenchmarkDataset":
        """Load benchmark tasks from a YAML or JSON file."""
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Benchmark dataset file not found: {p}")

        content = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif p.suffix == ".json":
            data = json.loads(content)
        else:
            # Try YAML parser as fallback for general markup
            try:
                data = yaml.safe_load(content)
            except Exception:
                data = json.loads(content)

        tasks_raw: List[Dict[str, Any]] = []
        version = "v1"

        if isinstance(data, list):
            tasks_raw = data
        elif isinstance(data, dict):
            version = data.get("version", data.get("dataset", "v1"))
            tasks_raw = data.get("tasks", [])
        else:
            raise ValueError(f"Unrecognized benchmark dataset structure in {p}")

        tasks: List[BenchmarkTask] = []
        for item in tasks_raw:
            gold_dict = item.get("gold", {})
            gold = GoldReference(
                symbols=list(gold_dict.get("symbols", []) or []),
                files=list(gold_dict.get("files", []) or []),
                related_symbols=list(gold_dict.get("related_symbols", []) or []),
                dependencies=list(gold_dict.get("dependencies", []) or []),
                tests=list(gold_dict.get("tests", []) or []),
                constraints=list(gold_dict.get("constraints", []) or []),
                excluded=list(gold_dict.get("excluded", []) or []),
            )
            task = BenchmarkTask(
                id=str(item.get("id", "")),
                task=str(item.get("task", "")).strip(),
                repository=str(item.get("repository", "sample_repo")),
                category=str(item.get("category", "General")),
                gold=gold,
            )
            tasks.append(task)

        dataset = cls(tasks=tasks, version=version)
        errs = dataset.validate()
        if errs:
            raise ValueError(f"Invalid benchmark dataset: {'; '.join(errs)}")

        return dataset

    def save_file(self, path: Union[Path, str]) -> None:
        """Save benchmark dataset to YAML or JSON."""
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self.version,
            "tasks": [t.to_dict() for t in self.tasks],
        }

        if p.suffix in (".yaml", ".yml"):
            with open(p, "w", encoding="utf-8") as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False)
        else:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
