"""Objective token accounting for the A/B experiment.

tokens ~= chars/4. File sizes are read from disk so numbers are reproducible and
independent of which files the measuring agent happened to open.

Usage:
    # size a set of files (relative to the dcnc repo root)
    python ledger.py files testing/dcnc backend/core/engines/zipcode_engine.py ...

    # summarize an arm's per-task ledger JSONs into a totals table
    python ledger.py totals benchmarks/dcnc-eval
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def file_tokens(repo_root: str, rel_paths: list[str]) -> dict:
    root = Path(repo_root)
    rows = []
    total_chars = 0
    for rp in rel_paths:
        p = root / rp
        if p.exists():
            chars = len(p.read_text(encoding="utf-8", errors="replace"))
        else:
            chars = 0
        rows.append({"file": rp, "chars": chars, "tokens": round(chars / 4)})
        total_chars += chars
    return {"rows": rows, "total_chars": total_chars, "total_tokens": round(total_chars / 4)}


def totals(eval_dir: str) -> dict:
    base = Path(eval_dir)
    out = {}
    for arm in ("arm1", "arm2"):
        arm_dir = base / arm
        if not arm_dir.exists():
            continue
        arm_total = 0
        tasks = {}
        for jf in sorted(arm_dir.glob("task-*.json")):
            data = json.loads(jf.read_text(encoding="utf-8"))
            t = data.get("total_tokens", 0)
            tasks[jf.stem] = t
            arm_total += t
        out[arm] = {"per_task": tasks, "total_tokens": arm_total}
    if "arm1" in out and "arm2" in out:
        a1 = out["arm1"]["total_tokens"]
        a2 = out["arm2"]["total_tokens"]
        out["savings"] = {
            "arm1_total_tokens": a1,
            "arm2_total_tokens": a2,
            "absolute_saved": a1 - a2,
            "reduction_pct": round(100.0 * (a1 - a2) / a1, 1) if a1 else 0.0,
        }
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "files":
        repo_root, *rels = argv[1:]
        print(json.dumps(file_tokens(repo_root, rels), indent=2))
        return 0
    if cmd == "totals":
        print(json.dumps(totals(argv[1]), indent=2))
        return 0
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
