"""Standard Model Context Protocol (MCP) server for external low-context AI coding agents."""

import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from repopeek.query.engine import GraphQueryEngine


class RepoPeekMCPServer:
    """Stdio JSON-RPC MCP server exposing RepoPeek intelligence tools to AI coding agents."""

    def __init__(self, engine: GraphQueryEngine) -> None:
        self.engine = engine

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
                    "serverInfo": {"name": "repopeek-mcp", "version": "0.1.0"},
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
                            "name": "repopeek_lookup",
                            "description": "Lookup node card by symbol or URI (<80 tokens)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "repopeek_neighbors",
                            "description": "Get direct incoming and outgoing relational edges",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "node_id": {"type": "string"},
                                    "direction": {"type": "string", "enum": ["both", "incoming", "outgoing"]},
                                },
                                "required": ["node_id"],
                            },
                        },
                        {
                            "name": "repopeek_impact",
                            "description": "Compute upstream blast radius answering 'If I change X, what breaks?'",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "target": {"type": "string"},
                                    "max_depth": {"type": "integer", "default": 5},
                                },
                                "required": ["target"],
                            },
                        },
                        {
                            "name": "repopeek_data_trace",
                            "description": "Trace variable def-use and data entity flows across language boundaries",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"entity": {"type": "string"}},
                                "required": ["entity"],
                            },
                        },
                        {
                            "name": "repopeek_context_pack",
                            "description": "Produce the minimal sufficient context pack (<500 tokens) for safe edits",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "targets": {"type": "array", "items": {"type": "string"}},
                                    "token_budget": {"type": "integer", "default": 1500},
                                },
                                "required": ["targets"],
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
        try:
            if tool_name == "repopeek_lookup":
                card = self.engine.lookup(args.get("query", ""))
                res_text = json.dumps(card.model_dump(exclude_none=True), indent=2) if card else "Node not found."

            elif tool_name == "repopeek_neighbors":
                res = self.engine.neighbors(args.get("node_id", ""), direction=args.get("direction", "both"))
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_impact":
                res = self.engine.impact(args.get("target", ""), max_depth=args.get("max_depth", 5))
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_data_trace":
                res = self.engine.data_trace(args.get("entity", ""))
                res_text = json.dumps(res, indent=2)

            elif tool_name == "repopeek_context_pack":
                targets = args.get("targets", [])
                budget = args.get("token_budget", 1500)
                pack = self.engine.context_pack(targets, token_budget=budget)
                res_text = pack.to_markdown()

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool '{tool_name}'"},
                }

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
