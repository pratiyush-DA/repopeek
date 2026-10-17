"""Minimal stdio JSON-RPC MCP client harness for the dcnc RepoPeek evaluation.

Spawns the RepoPeek MCP server once (via the eval .venv), performs the MCP
handshake, then issues a batch of tools/call requests, recording per-call
latency and payload size. Captures the server's stderr session summary line.

Usage:
    python mcp_client.py <repo_path> <calls.json> <out.json>

calls.json: list of {"name": <tool>, "arguments": {...}} objects.
out.json:   written with per-call results, latency_ms, chars, and the final
            stderr summary line emitted by the server on shutdown.

This is pure stdlib so it runs under the eval venv without extra deps.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path


def _repopeek_exe() -> str:
    """Resolve the repopeek entry inside the eval venv, falling back to module."""
    here = Path(__file__).resolve()
    # repo root is two levels up: benchmarks/dcnc-eval/ -> repo root
    root = here.parent.parent.parent
    exe = root / ".venv" / "Scripts" / "repopeek.exe"
    if exe.exists():
        return str(exe)
    return "repopeek"


def run_batch(repo_path: str, calls: list[dict]) -> dict:
    exe = _repopeek_exe()
    proc = subprocess.Popen(
        [exe, "--repo-path", repo_path, "--serve-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    stderr_buf: list[str] = []

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_buf.append(line.rstrip("\n"))

    t_err = threading.Thread(target=_drain_stderr, daemon=True)
    t_err.start()

    assert proc.stdin is not None and proc.stdout is not None

    def _send(obj: dict) -> None:
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def _recv() -> dict:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed stdout unexpectedly")
        return json.loads(line)

    results: list[dict] = []

    # Handshake
    _send({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    init = _recv()
    _send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    for i, call in enumerate(calls, start=1):
        req = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": {"name": call["name"], "arguments": call.get("arguments", {})},
        }
        t0 = time.perf_counter()
        _send(req)
        resp = _recv()
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Extract text payload length (MCP returns result.content[].text)
        chars = 0
        text_payload = ""
        err = None
        if "error" in resp:
            err = resp["error"]
        else:
            content = resp.get("result", {}).get("content", [])
            for c in content:
                if c.get("type") == "text":
                    text_payload += c.get("text", "")
            chars = len(text_payload)
        results.append({
            "name": call["name"],
            "arguments": call.get("arguments", {}),
            "latency_ms": latency_ms,
            "chars": chars,
            "est_tokens": round(chars / 4),
            "error": err,
            "text": text_payload,
        })

    # Close stdin so the server's stdin loop ends and it prints the summary.
    proc.stdin.close()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    t_err.join(timeout=5)

    return {
        "server_info": init.get("result", {}).get("serverInfo", {}),
        "calls": results,
        "stderr": stderr_buf,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    repo_path, calls_file, out_file = argv
    calls = json.loads(Path(calls_file).read_text(encoding="utf-8-sig"))
    report = run_batch(repo_path, calls)
    Path(out_file).write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Console summary
    total_chars = sum(c["chars"] for c in report["calls"])
    print(f"server={report['server_info']}")
    for c in report["calls"]:
        status = "ERR" if c["error"] else "ok"
        print(f"  [{status}] {c['name']:<26} {c['latency_ms']:>8} ms  {c['chars']:>7} chars  ~{c['est_tokens']} tok")
    print(f"TOTAL returned: {total_chars} chars (~{round(total_chars/4)} tokens) across {len(report['calls'])} calls")
    for line in report["stderr"]:
        print(f"  stderr> {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
