"""Compute Arm 1 (file-first) per-task ledgers from objective file sizes (5 New Tasks).

File-first cost = Σ tokens of every file a cold agent must open in full to
locate the change, understand the contract, and assess blast radius. File sets
are the realistic grep-driven discovery paths documented in methodology.md.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ledger import file_tokens  # noqa: E402

ROOT = "testing/dcnc"
E = "backend/core/engines/"
I = "backend/core/interfaces/"

SETS = {
    "task-1": [E + "ssn_engine.py", E + "base_engine.py"],
    "task-2": [E + "url_engine.py", E + "base_engine.py"],
    "task-3": [E + "base_engine.py", "backend/core/registry.py",
               E + "ssn_engine.py", E + "__init__.py"],
    "task-4": [I + "validator_interface.py", E + "base_engine.py",
               E + "zipcode_engine.py", E + "email_engine.py", E + "phone_engine.py",
               E + "url_engine.py", E + "ip_address_engine.py", E + "name_engine.py",
               E + "boolean_engine.py", E + "ssn_engine.py",
               E + "generic_string_engine.py", E + "generic_numeric_engine.py"],
    "task-5": [I + "detector_interface.py",
               "backend/core/detection/workflow_detector.py",
               "backend/core/detection/detection_cache.py",
               "backend/core/correction/output_writer.py",
               "backend/services/pipeline_service.py"],
}


def main() -> int:
    out_dir = os.path.join(os.path.dirname(__file__), "arm1")
    os.makedirs(out_dir, exist_ok=True)
    grand = 0
    for tid, files in SETS.items():
        r = file_tokens(ROOT, files)
        rec = {
            "arm": "file-first",
            "task": tid,
            "files_opened": r["rows"],
            "total_chars": r["total_chars"],
            "total_tokens": r["total_tokens"],
        }
        with open(os.path.join(out_dir, f"{tid}.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
        grand += r["total_tokens"]
        print(f"{tid}: {len(files):>2} files, {r['total_tokens']:>5} tokens")
    print("ARM1 GRAND TOTAL:", grand, "tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
