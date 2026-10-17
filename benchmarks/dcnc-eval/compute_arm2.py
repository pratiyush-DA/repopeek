"""Compute Arm 2 (RepoPeek-first) ledgers for BOTH navigation variants (5 New Tasks).

Variant A (resolve-first): the agent leads with repopeek_resolve (also sanctioned
    by the steering rule). Payloads from arm2/nav_out.json.
Variant B (context-first): the agent leads with repopeek_context (the README's
    intended lean path). Payloads from arm2/context_out.json.

Cost (either variant) = RepoPeek payload tokens + edit-target file tokens.
The canonical arm2/task-N.json uses Variant B (context-first), the tool the
product documents as primary; Variant A totals are recorded in savings_summary.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ledger import file_tokens  # noqa: E402

ROOT = "testing/dcnc"
E = "backend/core/engines/"
I = "backend/core/interfaces/"
HERE = os.path.dirname(__file__)

# resolve-first call indices in nav_out.json
RESOLVE_CALLS = {
    "task-1": [0, 1], "task-2": [2, 3], "task-3": [4, 5, 6],
    "task-4": [7, 8, 9], "task-5": [10, 11, 12],
}
# context-first call indices in context_out.json (one context call per task)
CONTEXT_CALLS = {
    "task-1": [0], "task-2": [1], "task-3": [2], "task-4": [3], "task-5": [4],
}

EDIT_TARGETS = {
    "task-1": [E + "ssn_engine.py"],
    "task-2": [E + "url_engine.py"],
    "task-3": [E + "__init__.py"],
    "task-4": [I + "validator_interface.py", E + "zipcode_engine.py", E + "email_engine.py",
               E + "phone_engine.py", E + "url_engine.py", E + "ip_address_engine.py",
               E + "name_engine.py", E + "boolean_engine.py", E + "ssn_engine.py",
               E + "generic_string_engine.py", E + "generic_numeric_engine.py"],
    "task-5": [I + "detector_interface.py",
               "backend/core/detection/workflow_detector.py",
               "backend/core/correction/output_writer.py"],
}


def payloads(path, idx_map):
    data = json.load(open(path, encoding="utf-8"))
    calls = data["calls"]
    return {t: sum(calls[i]["est_tokens"] for i in idxs) for t, idxs in idx_map.items()}


def main() -> int:
    resolve_p = payloads(os.path.join(HERE, "arm2", "nav_out.json"), RESOLVE_CALLS)
    context_p = payloads(os.path.join(HERE, "arm2", "context_out.json"), CONTEXT_CALLS)

    arm1 = {t: json.load(open(os.path.join(HERE, "arm1", f"{t}.json"), encoding="utf-8"))["total_tokens"]
            for t in EDIT_TARGETS}

    summary = {"per_task": {}, "variant_A_resolve_first": {}, "variant_B_context_first": {}}
    tot_a = tot_b = tot_1 = 0
    for t in EDIT_TARGETS:
        et = file_tokens(ROOT, EDIT_TARGETS[t])["total_tokens"]
        a = resolve_p[t] + et
        b = context_p[t] + et
        tot_a += a; tot_b += b; tot_1 += arm1[t]
        # canonical ledger = context-first
        rec = {
            "arm": "repopeek-first (context)",
            "task": t,
            "repopeek_payload_tokens": context_p[t],
            "edit_target_tokens": et,
            "total_tokens": b,
            "variant_resolve_first_total": a,
        }
        json.dump(rec, open(os.path.join(HERE, "arm2", f"{t}.json"), "w", encoding="utf-8"), indent=2)
        summary["per_task"][t] = {
            "arm1_file_first": arm1[t],
            "arm2_resolve_first": a,
            "arm2_context_first": b,
        }
        print(f"{t}: file-first={arm1[t]:>6} | resolve-first={a:>6} | context-first={b:>6}")

    def pct(base, other):
        return round(100.0 * (base - other) / base, 1) if base else 0.0

    summary["totals"] = {
        "arm1_file_first": tot_1,
        "arm2_resolve_first": tot_a,
        "arm2_context_first": tot_b,
        "reduction_pct_resolve_first": pct(tot_1, tot_a),
        "reduction_pct_context_first": pct(tot_1, tot_b),
    }
    json.dump(summary, open(os.path.join(HERE, "savings_summary.json"), "w", encoding="utf-8"), indent=2)
    print(f"\nTOTAL  file-first={tot_1}  resolve-first={tot_a} ({pct(tot_1, tot_a)}%)  "
          f"context-first={tot_b} ({pct(tot_1, tot_b)}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
