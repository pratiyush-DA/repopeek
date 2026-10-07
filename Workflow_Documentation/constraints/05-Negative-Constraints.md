# Negative Constraints and Forbidden Behaviors

This document treats **negative knowledge** as a first-class architectural specification. It explicitly defines what RepoPeek must **NOT** do, forbidden modifications, intentionally excluded functionality, dangerous anti-patterns, and architectural constraints that prevent seemingly obvious implementations.

---

## 1. Forbidden Modifications to Target Repositories

### 1.1 Zero In-Place Code Editing
- **Rule:** RepoPeek must **NEVER** edit, refactor, auto-format, or modify source code files in the target repository.
- **Why Forbidden:** RepoPeek is strictly an intelligence, analysis, and context-generation engine. Modifying user code violates the principle of separation of concerns and creates catastrophic data-loss risks. Code changes must be performed by the developer or an agent acting on a generated `ChangePlan`.
- **Enforcement:** All tools, queries, and parsers open source files in read-only mode (`r` or `rb`).

### 1.2 No Git Worktree Alterations
- **Rule:** The Git temporal miner in [repopeek/temporal/miner.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/temporal/miner.py) must **NEVER** create commits, checkout branches, rebase, or alter the git repository index.
- **Why Forbidden:** Mining historical co-change probabilities requires reading git commit logs (`git log --name-only`). Any modification of git state would disrupt active developer workflows.

---

## 2. Forbidden Architectural Patterns

### 2.1 No In-Place Graph File Mutation
- **Rule:** Persistent JSON files (`graph.json`, `manifest.json`) must **NEVER** be updated in-place via read-write file streams or append operations.
- **Why Forbidden:** An abrupt kill signal (`SIGKILL`, power failure, OS task cancellation) during an in-place write corrupts the JSON document, rendering the entire graph unparseable.
- **Mandated Pattern:** Always build new artifacts inside a temporary directory (`.tmp_build_<uuid>`) and execute an atomic directory swap.

### 2.2 No Bare / Unnamespaced Identifier Collisions (RP-003)
- **Rule:** Parsers and graph builders must **NEVER** insert unnamespaced common identifiers (e.g. `next`, `id`, `open`, `app`, `config`) into the global graph without language/file scoping.
- **Why Forbidden:** Discovered in [repopeek-cross-language-graph-collision-and-namespace-isolation-trap](file:///C:/Users/pkumar2/.gemini/antigravity-ide/knowledge/repopeek-cross-language-graph-collision-and-namespace-isolation-trap/artifacts/RepoPeek%20Cross-Language%20Graph%20Collision%20and%20Namespace%20Isolation%20Trap.md). A bare `next` identifier bridges Python's built-in `next()` function with Next.js framework imports in TypeScript, collapsing two completely disconnected language subtrees into a single giant component.

### 2.3 No Hard Cloud LLM Dependencies
- **Rule:** The indexing pipeline must **NEVER** crash or abort because the Groq LLM API is unavailable, missing credentials, or returning HTTP 429 rate limits.
- **Why Forbidden:** Offline capability and local CI execution are strict requirements.
- **Mandated Pattern:** Always degrade gracefully through the 5-tier fallback cascade to AST invariants and deterministic template heuristics.

---

## 3. Intentionally Excluded Functionality

### 3.1 No Full Semantic Type-Checker Implementation
- **What is Excluded:** RepoPeek does not implement full TypeScript language-service type resolution, C++ template instantiation, or whole-program bytecode simulation.
- **Why Excluded:** Building a full compiler type checker for multiple languages would require gigabytes of compiler toolchains and increase indexing latency by $100\times$. Static AST extraction combined with heuristic symbol resolution delivers 95% of dependency accuracy at `<5%` of the runtime cost.

### 3.2 No Direct Network Ports Opened for Agent Tooling
- **What is Excluded:** The MCP server does not open HTTP or WebSocket network ports.
- **Why Excluded:** Network ports create port conflict errors (`EADDRINUSE`), firewall permission prompts, and localhost security vulnerabilities. Stdio communication is completely isolated and lifecycle-managed by the parent AI editor.

---

## 4. Dangerous Assumptions to Avoid

| Seemingly Obvious Idea | Why It Is Dangerous | Correct Approach |
|---|---|---|
| **Rely on `pytest` bare discovery from repo root** | Crawls into `testing/da-assistant/` and fails on uninstalled Django dependencies. | Always invoke `python -m pytest tests`. |
| **Store source code strings inside all NodeCards in RAM** | Multi-hundred-thousand-line repositories exhaust developer memory (OOM). | Store code coordinates (`Span(file, start, end)`) and read slices on demand. |
| **Send `print()` debug statements in MCP tools** | Corrupts the stdio JSON-RPC stream, causing Cursor or Claude Desktop to crash. | Direct all debug logs strictly to `sys.stderr`. |
| **Trust LLM narrative over AST purity flag** | Frontier LLMs frequently hallucinate network or DB operations on pure functions. | `FactVerifier` prunes story claims that contradict AST facts. |
| **Traverse graph without depth caps** | Circular imports and mutual recursion cause stack overflow or infinite loops. | Maintain `visited` set and enforce depth $H \le 3$ with probability attenuation. |
