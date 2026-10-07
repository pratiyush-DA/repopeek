# Component: Cross-Language HTTP Boundary Bridge

## 1. Overview
The HTTP boundary bridge connects client frontend API calls (TypeScript/JavaScript `fetch`, `axios`, `apiClient`) to backend route handlers (Python FastAPI, Flask, Starlette, Node Express) using path parameter wildcard normalization (`:param`).

- **Package:** `repopeek.bridges`
- **Source File:** [`repopeek/bridges/http.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/bridges/http.py)
- **Primary Tests:**
  - [`tests/test_http_bridge.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_http_bridge.py)
  - [`tests/test_data_flow_and_bridges.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_data_flow_and_bridges.py)

---

## 2. Path Normalization Logic (`normalize_route_path`)

Different web frameworks and client libraries express dynamic route parameters with conflicting syntactic notations. RepoPeek normalizes all parameter expressions into standard `:param` segments:

| Framework / Client Pattern | Raw Input | Normalized Template |
|---|---|---|
| FastAPI / Starlette | `/api/users/{user_id}` | `/api/users/:param` |
| Express / React Router | `/api/users/:userId` | `/api/users/:param` |
| Flask | `/api/users/<int:user_id>` | `/api/users/:param` |
| JavaScript Template Literal | `${this.apiUrl}/users/${id}` | `/users/:param` |
| Literal Client Request | `/api/users/10492` | `/api/users/:param` |
| UUID Client Request | `/api/orders/a1b2c3d4-e5f6-7890-1234-56789abcdef0` | `/api/orders/:param` |

### Parameter Token Regex
```python
PARAM_TOKEN_RE = re.compile(
    r"^(:[a-zA-Z0-9_$]+|\{[a-zA-Z0-9_$]+\}|<[a-zA-Z0-9_$:.]+>|\$\{[a-zA-Z0-9_$.]+\}|\d+|[0-9a-fA-F-]{36})$"
)
```

---

## 3. Route Matching and Edge Synthesis

### Matching Criteria (`paths_match`)
1. **Segment Length Matching:** If segments have identical length, compares segment-by-segment allowing `:param` to match any literal token.
2. **Suffix Subpath Matching:** If segment lengths differ (e.g. client requests `/users/:param` while server defines base prefix `/api/v1/users/:param`), matches the common trailing suffix.
3. **HTTP Verb Compatibility:**
   - Client HTTP method (GET, POST, PUT, DELETE, PATCH) must match server route decorator method.
   - If server method is `"ANY"`, matches all client verbs.

### Edge Synthesis
When a match is confirmed:
- Creates `Edge`:
  - `src`: Caller frontend node ID.
  - `dst`: Route handler backend node ID.
  - `type`: `EdgeType.INVOKES`.
  - `confidence`: `Confidence.RESOLVED`.
  - `evidence`: `Evidence(how_derived="http_boundary(<method> <raw_url> -> <route>)")`.

---

## 4. Known Limitation: Declarative Django Route Blindspot

> [!IMPORTANT]
> **Known Limitation (Defect RP-001):**
> As discovered during real-world evaluation on `da-assistant`, `HttpBoundaryBridge` relies exclusively on decorator regexes (`ROUTE_DECORATOR_RE`, `FLASK_ROUTE_RE`, `EXPRESS_ROUTE_RE`).
> It does NOT currently parse declarative Django / DRF routing lists (`urlpatterns = [path("...", View.as_view())]`). In Django projects, route discovery will return 0 routes unless endpoints use decorators.
