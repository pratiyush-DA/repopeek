---
id: feat-http-bridge
type: feature
title: Cross-Language HTTP Boundary Bridge
summary: Bridges TypeScript/JavaScript client API calls to backend route handlers (FastAPI, Flask, Express) using wildcard path parameter normalization and typed INVOKES edges.
status: verified
tags: [http, bridge, cross-language, routes, blast-radius]
code_refs: [repopeek/bridges/http.py, repopeek/bridges/__init__.py, repopeek/parsers/python.py, repopeek/parsers/typescript.py, repopeek/graph/builder.py, repopeek/graph/lenses.py, repopeek/query/engine.py, repopeek/cli.py]
depends_on: ['[[feat-python-parser]]', '[[feat-typescript-parser]]', '[[feat-graph-construction]]', '[[plan-phase-3]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---

# Cross-Language HTTP Boundary Bridge

## 1. Executive Summary & Purpose
Fullstack systems commonly fracture static code graphs across the network boundary: a TypeScript React/Vue/Node client invokes an endpoint (`fetch('/api/v1/users/' + id)` or `axios.post('/api/v1/users')`) defined in a Python FastAPI/Flask backend or Express server. Without bridging this gap, changes to backend route models show zero frontend blast radius, and frontend refactors cannot trace API dependencies.

The `HttpBoundaryBridge` resolves this boundary deterministically by:
1. Normalizing heterogeneous URL path templates and dynamic parameters (`:param`, `{param}`, `<param>`, `${param}`) to a unified `:param` representation.
2. Extracting server endpoints from route decorators (`@app.get(...)`, `@router.post(...)`, `@bp.route(...)`, Express `app.get(...)`).
3. Extracting client invocations from `fetch`, `axios`, and `apiClient` calls.
4. Matching normalized paths and compatible HTTP methods to synthesize typed `INVOKES` edges with evidence metadata.

## 2. Path Parameter Normalization Algorithm
- Query strings (`?foo=bar`) and URL fragments (`#section`) are stripped.
- Scheme and authority prefixes (`http://localhost:8000/api/...`) are stripped to domain-relative paths.
- Template string interpolations (e.g. `${API_URL}/users`, `${this.baseUrl}/users`) are stripped to root path segments.
- Path tokens matching `:param`, `{param}`, `<type:param>`, `${param}`, or numeric IDs are normalized to `:param`.
- Suffix matching links relative frontend requests (e.g. `/users/:param`) to reverse-proxied or mounted backend routes (e.g. `/api/users/:param`).

## 3. Graph & Blast Radius Integration
- Client callers and server route handlers are connected with canonical `EdgeType.INVOKES` edges (prior confidence 0.75).
- Upstream blast radius traversals from a backend route handler immediately flag affected frontend client callers.
- Downstream blast radius traversals from a frontend caller immediately discover backend API dependencies.
- `get_bridges_lens()` incorporates cross-language `INVOKES` edges for specialized architectural visualization.
- `repopeek --routes` and `GraphQueryEngine.http_routes()` provide unified route introspection.
