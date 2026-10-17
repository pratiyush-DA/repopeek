"""Standard Model Context Protocol (MCP) server for external low-context AI coding agents."""

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

from repopeek.query.engine import GraphQueryEngine
from repopeek.query.pack import ContextPack
from repopeek.query.telemetry import TelemetrySession, build_session


class RepoPeekMCPServer:
    """Stdio JSON-RPC MCP server exposing RepoPeek intelligence tools to AI coding agents."""

    def __init__(self, engine: GraphQueryEngine, telemetry: Optional[TelemetrySession] = None) -> None:
        self.engine = engine
        self.telemetry = telemetry if telemetry is not None else build_session()

    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming JSON-RPC protocol message."""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "repopeek-mcp", "version": "0.3.0"},
                    "capabilities": {"tools": {}},
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "repopeek_context",
                            "description": "Compile task into token-reduced context package and change plan. Best for multi-file features and unfamiliar code. For known single-file leaf changes, open the file directly to avoid tool overhead.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string", "description": "Natural language engineering task"},
                                    "budget": {"type": "integer", "default": 1500, "description": "Token budget cap"},
                                    "level": {"type": "integer", "enum": [1, 2, 3], "default": 2, "description": "Progressive disclosure level (1: brief, 2: standard, 3: full)"},
                                    "format": {"type": "string", "enum": ["markdown", "json"], "default": "markdown", "description": "Output rendering format"},
                                },
                                "required": ["task"],
                            },
                        },
                        {
                            "name": "repopeek_plan",
                            "description": "Generate a risk-assessed, step-by-step engineering change plan with estimated blast radius and affected files",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string", "description": "Natural language engineering task"},
                                },
                                "required": ["task"],
                            },
                        },
                        {
                            "name": "repopeek_impact",
                            "description": "Compute mathematical traversal confidence blast radius answering 'If I change X, what breaks?'. Always call before modifying shared interfaces or functions.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "target": {"type": "string", "description": "Target symbol or node ID"},
                                    "max_depth": {"type": "integer", "default": 5, "description": "Max hop traversal depth"},
                                    "direction": {"type": "string", "enum": ["both", "upstream", "downstream"], "default": "both"},
                                    "threshold": {"type": "number", "default": 0.20, "description": "Confidence inclusion threshold"},
                                },
                                "required": ["target"],
                            },
                        },
                        {
                            "name": "repopeek_routes",
                            "description": "Discover server HTTP route endpoints, client API calls (fetch/axios), and cross-boundary fullstack linkages",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                            },
                        },
                        {
                            "name": "repopeek_co_changes",
                            "description": "Query historical git commit co-change patterns, conditional probabilities P(B|A), and temporal coupling",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "target": {"type": "string", "description": "Target file path or symbol"},
                                },
                                "required": ["target"],
                            },
                        },
                        {
                            "name": "repopeek_resolve",
                            "description": "Resolve a natural language engineering task into candidate symbols via AST + SQLite FTS5 BM25 + Reciprocal Rank Fusion",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string", "description": "Natural language task description or search query"},
                                    "query": {"type": "string", "description": "Alias for task description or search query"},
                                    "limit": {"type": "integer", "default": 5, "description": "Max candidates to return (default: 5)"},
                                    "include_story": {"type": "boolean", "default": False, "description": "Include full multi-line story narrative (default: false)"},
                                },
                            },
                        },
                        {
                            "name": "repopeek_lookup",
                            "description": "Ultra-compact symbol contract retrieval (<70 tokens). Returns signature, location, and blast radius. Best for quick symbol checks before editing.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Symbol name, function name, or node ID"},
                                    "include_snippet": {"type": "boolean", "default": False, "description": "Include exact source code span snippet"},
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "repopeek_neighbors",
                            "description": "Get direct incoming and outgoing relational edges",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "node_id": {"type": "string", "description": "Target node ID"},
                                    "direction": {"type": "string", "enum": ["both", "incoming", "outgoing"], "default": "both"},
                                },
                                "required": ["node_id"],
                            },
                        },
                        {
                            "name": "repopeek_data_trace",
                            "description": "Trace variable def-use and data entity flows across language boundaries",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "entity": {"type": "string", "description": "Variable name or database table name"},
                                },
                                "required": ["entity"],
                            },
                        },
                        {
                            "name": "repopeek_context_pack",
                            "description": "Produce the minimal sufficient context pack (<500 tokens) for safe target edits",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "targets": {"type": "array", "items": {"type": "string"}, "description": "Target symbol names"},
                                    "token_budget": {"type": "integer", "default": 1500, "description": "Max token budget"},
                                    "include_snippet": {"type": "boolean", "default": False, "description": "Include exact source snippet"},
                                },
                                "required": ["targets"],
                            },
                        },
                        {
                            "name": "repopeek_session_stats",
                            "description": "Session rollup of RepoPeek usage with ESTIMATED context savings (tokens and file reads the agent avoided this session). Savings are modeled, not measured.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "format": {"type": "string", "enum": ["markdown", "json"], "default": "markdown", "description": "Output rendering format"},
                                },
                            },
                        },
                        {
                            "name": "repopeek_god_nodes",
                            "description": "Identify top god nodes (most connected core abstractions) with degree centrality and file citations",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "top_n": {"type": "integer", "default": 10, "description": "Number of top god nodes to return"},
                                },
                            },
                        },
                        {
                            "name": "repopeek_cycles",
                            "description": "Detect circular dependencies and import cycles in the repository",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                            },
                        },
                        {
                            "name": "repopeek_communities",
                            "description": "Partition graph into modular functional communities with cohesion scores and member counts",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "resolution": {"type": "number", "default": 1.0, "description": "Clustering resolution (>1.0: smaller, <1.0: larger)"},
                                    "top_n": {"type": "integer", "default": 10, "description": "Max top communities by size to return"},
                                },
                            },
                        },
                        {
                            "name": "repopeek_suggest_questions",
                            "description": "Generate actionable architectural questions concerning god nodes, cycles, and cross-boundary couplings",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "top_n": {"type": "integer", "default": 7, "description": "Number of suggested questions"},
                                },
                            },
                        },
                        {
                            "name": "repopeek_report",
                            "description": "Generate the full Markdown Graph Report (GRAPH_REPORT.md) audit trail",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project_name": {"type": "string", "description": "Optional human project name"},
                                },
                            },
                        },
                    ]
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            return self._execute_tool(req_id, tool_name, tool_args)

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }

    def _execute_tool(self, req_id: Any, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool calls to GraphQueryEngine."""
        start = time.perf_counter()
        # Savings attribution for this call; only context/pack tools set a non-zero
        # baseline, because only they displace real file reads.
        tokens_saved_estimate = 0
        files_avoided_estimate = 0
        try:
            if tool_name == "repopeek_session_stats":
                fmt = args.get("format", "markdown")
                if fmt == "json":
                    res_text = json.dumps(self.telemetry.to_dict(), indent=2)
                else:
                    d = self.telemetry.to_dict()
                    res_text = "\n".join([
                        "# RepoPeek Session Stats (estimated savings)",
                        "",
                        self.telemetry.summary_line(),
                        "",
                        f"- Uptime: {d['session_uptime_sec']}s",
                        f"- Tool calls: {d['total_tool_calls']}",
                        f"- Tokens returned: ~{d['tokens_returned']}",
                        f"- Tokens saved (est.): ~{d['tokens_saved_estimate']}",
                        f"- File reads avoided (est.): ~{d['files_avoided_estimate']}",
                        f"- Estimated reduction: {d['estimated_reduction_pct']}%",
                        "",
                        f"> {d['note']}",
                    ])

            elif tool_name == "repopeek_context":
                task_str = args.get("task", "")
                budget = int(args.get("budget", 1500))
                level = int(args.get("level", 2))
                fmt = args.get("format", "markdown")
                pkg = self.engine.compile_context(task=task_str, budget=budget, level=level)
                if fmt == "json":
                    res_text = json.dumps(pkg.to_dict(), indent=2)
                else:
                    res_text = pkg.to_markdown(level=level)
                # The compiler already computed the raw-read baseline; savings is the
                # difference between that baseline and the pack we actually returned.
                tokens_saved_estimate = max(0, pkg.raw_file_tokens - pkg.estimated_tokens)
                files_avoided_estimate = len(pkg.affected_files)

            elif tool_name == "repopeek_plan":
                task_str = args.get("task", "")
                plan = self.engine.change_plan(task=task_str)
                res_text = plan.to_markdown()

            elif tool_name == "repopeek_impact":
                target = args.get("target", "")
                max_depth = int(args.get("max_depth", 5))
                direction = args.get("direction", "both")
                threshold = float(args.get("threshold", 0.20))
                res = self.engine.impact(
                    target,
                    max_depth=max_depth,
                    direction=direction,
                    confidence_threshold=threshold,
                )
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_routes":
                res = self.engine.http_routes()
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_co_changes":
                target = args.get("target", "")
                res = self.engine.co_changes(target)
                if not res:
                    res_text = json.dumps({
                        "co_changes": [],
                        "note": f"No git co-change history found for '{target}' (shallow clone or squashed history).",
                    }, indent=2)
                else:
                    res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_resolve":
                task_str = (args.get("task") or args.get("query") or "").strip()
                if not task_str:
                    res_text = json.dumps({"error": "Either 'task' or 'query' parameter is required."}, indent=2)
                else:
                    limit = int(args.get("limit", 5))
                    inc_story = bool(args.get("include_story", False))
                    res = self.engine.resolve_task(task_str, limit=limit, include_story=inc_story)
                    res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_lookup":
                query = args.get("query", "")
                include_snip = bool(args.get("include_snippet", False))
                card = self.engine.lookup(query, include_snippet=include_snip)
                if not card:
                    res_text = "Node not found."
                else:
                    lean = {
                        "id": card.id,
                        "kind": card.kind,
                        "sig": card.sig,
                        "file": card.span.file if card.span else None,
                        "lines": f"{card.span.start}-{card.span.end}" if card.span else None,
                        "blast_radius": self.engine.compute_blast(card.id),
                    }
                    if include_snip and getattr(card, "snippet", None):
                        lean["snippet"] = card.snippet
                    res_text = json.dumps(lean, indent=2)

            elif tool_name == "repopeek_neighbors":
                node_id = args.get("node_id", "")
                direction = args.get("direction", "both")
                res = self.engine.neighbors(node_id, direction=direction)
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_data_trace":
                entity = args.get("entity", "")
                res = self.engine.data_trace(entity)
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_context_pack":
                targets = args.get("targets", [])
                budget = int(args.get("token_budget", 1500))
                include_snip = bool(args.get("include_snippet", False))
                pack = self.engine.context_pack(targets, token_budget=budget, include_snippet=include_snip)
                res_text = pack.to_markdown()
                # ContextPack has no raw_file_tokens, so model the baseline from the
                # count of affected files (same avg-file assumption as the compiler).
                files_avoided_estimate = len(pack.affected_files)
                baseline = TelemetrySession.estimate_pack_baseline_tokens(files_avoided_estimate)
                tokens_saved_estimate = max(0, baseline - pack.estimated_tokens)

            elif tool_name == "repopeek_god_nodes":
                top_n = int(args.get("top_n", 10))
                gods = self.engine.get_god_nodes(top_n=top_n)
                res_text = json.dumps(gods, indent=2)

            elif tool_name == "repopeek_cycles":
                cycles = self.engine.get_cycles()
                res_text = json.dumps(cycles, indent=2)

            elif tool_name == "repopeek_communities":
                resolution = float(args.get("resolution", 1.0))
                top_n = int(args.get("top_n", args.get("limit", 10)))
                comms, labels = self.engine.get_communities(resolution=resolution)
                sorted_comms = sorted(comms.items(), key=lambda kv: len(kv[1]), reverse=True)
                summary = {
                    "total_communities": len(comms),
                    "returned_count": min(len(sorted_comms), top_n),
                    "communities": [
                        {
                            "id": cid,
                            "label": labels.get(cid, f"Community {cid}"),
                            "size": len(members),
                            "top_members": [m.split("::")[-1] for m in members[:5]],
                        }
                        for cid, members in sorted_comms[:top_n]
                    ],
                }
                res_text = json.dumps(summary, indent=2)

            elif tool_name == "repopeek_suggest_questions":
                from repopeek.graph.analysis import suggest_questions
                top_n = int(args.get("top_n", 7))
                questions = suggest_questions(self.engine.graph, top_n=top_n)
                res_text = json.dumps(questions, indent=2)

            elif tool_name == "repopeek_report":
                from repopeek.export.report import generate_graph_report
                pname = args.get("project_name") or (self.engine.repo_root.name if self.engine.repo_root else "Repository")
                res_text = generate_graph_report(self.engine.graph, project_name=pname)

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool '{tool_name}'"},
                }

            # Systemic payload guard: no tool may emit an unbounded blob. Per-tool caps keep
            # normal results small; this is the structural backstop that keeps any tool within
            # the ~15k budget (returns valid JSON, not a truncated/invalid fragment).
            MAX_TOOL_TEXT_CHARS = 30000
            if len(res_text) > MAX_TOOL_TEXT_CHARS:
                res_text = json.dumps({
                    "truncated": True,
                    "tool": tool_name,
                    "reason": (
                        f"payload {len(res_text)} chars exceeded the {MAX_TOOL_TEXT_CHARS}-char tool "
                        "budget; narrow the query or use repopeek_context for a focused pack"
                    ),
                    "preview": res_text[:2000],
                }, indent=2)

            # Record session telemetry. The session_stats tool is excluded so that
            # merely reading the rollup does not inflate the rollup it reports.
            if tool_name != "repopeek_session_stats":
                latency_ms = (time.perf_counter() - start) * 1000.0
                self.telemetry.record_call(
                    tool_name=tool_name,
                    latency_ms=latency_ms,
                    tokens_returned=ContextPack.estimate_tokens_from_text(res_text),
                    tokens_saved_estimate=tokens_saved_estimate,
                    files_avoided_estimate=files_avoided_estimate,
                )

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": res_text}]},
            }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }

    def run_stdio(self) -> None:
        """Run infinite stdio read-write loop processing MCP commands."""
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                    resp = self.handle_request(req)
                    if resp:
                        sys.stdout.write(json.dumps(resp) + "\n")
                        sys.stdout.flush()
                except Exception as e:
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {e}"},
                    }
                    sys.stdout.write(json.dumps(err_resp) + "\n")
                    sys.stdout.flush()
        finally:
            # Emit the session rollup on shutdown so savings are visible even when
            # the agent never calls repopeek_session_stats. stderr keeps the stdio
            # JSON-RPC channel clean.
            if self.telemetry.total_calls:
                print(self.telemetry.summary_line(), file=sys.stderr)
