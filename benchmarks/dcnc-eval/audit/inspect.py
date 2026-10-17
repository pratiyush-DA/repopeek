import json
import sys

d = json.load(open("benchmarks/dcnc-eval/audit/audit_out.json", encoding="utf-8"))
want = set(sys.argv[1:]) if len(sys.argv) > 1 else None
for c in d["calls"]:
    if want and c["name"] not in want:
        continue
    print("=" * 20, c["name"], f"({c['chars']} chars, {c['latency_ms']}ms)", "=" * 20)
    print((c["text"] or "")[:1100])
    print()
