# Deployment and Integration Models

RepoPeek supports four primary deployment patterns: local developer sidecar, AI editor MCP integration (Cursor, Claude Desktop, Antigravity), CI/CD quality gate, and containerized viewer service.

---

## 1. Local Developer Sidecar (Watch Daemon)

In local developer environments, RepoPeek runs as a lightweight background daemon keeping `.repopeek/` synchronized with code changes in real time.

### Starting the Daemon
```bash
repopeek --repo-path . --output-dir .repopeek --watch --watch-interval 1.0
```

### Background Execution
- **Linux/macOS (nohup / screen):**
  ```bash
  nohup repopeek --watch > .repopeek/daemon.log 2>&1 &
  ```
- **Windows (PowerShell background job):**
  ```powershell
  Start-Job -ScriptBlock { repopeek --watch }
  ```

---

## 2. AI Coding Agent MCP Integrations

RepoPeek provides a stdio MCP server that integrates directly into AI coding environments.

### 2.1 Claude Desktop Configuration
Add to `claude_desktop_config.json`:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "repopeek": {
      "command": "python",
      "args": [
        "-m",
        "repopeek.cli",
        "--repo-path",
        "/path/to/target/repository",
        "--serve-mcp"
      ],
      "env": {
        "PYTHONPATH": "/path/to/target/repository"
      }
    }
  }
}
```

### 2.2 Cursor IDE Configuration
Add to `.cursor/mcp.json` in your workspace root:

```json
{
  "mcpServers": {
    "repopeek": {
      "command": "repopeek",
      "args": ["--serve-mcp"]
    }
  }
}
```

### 2.3 Antigravity / Gemini CLI Configuration
Add to `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "repopeek": {
      "command": "repopeek",
      "args": ["--serve-mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

---

## 3. CI/CD Static Analysis Pipeline (GitHub Actions)

RepoPeek can be run during CI builds to construct repository graphs, verify architectural invariants, and enforce blast radius budgets on pull requests.

```yaml
name: RepoPeek Architectural Gate

on:
  pull_request:
    branches: [main]

jobs:
  repopeek-analysis:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Full history required for git temporal co-change mining

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install RepoPeek
        run: |
          pip install --upgrade pip
          pip install .

      - name: Run Deterministic Graph Construction
        run: |
          repopeek --repo-path . --output-dir .repopeek --offline

      - name: Upload Graph Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: repopeek-graph
          path: .repopeek/
          retention-days: 14
```

---

## 4. Containerized Web Viewer Deployment

To run RepoPeek as a containerized web viewer:

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install git for temporal history analysis
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY repopeek ./repopeek

RUN pip install --no-cache-dir .

EXPOSE 8765

ENTRYPOINT ["repopeek"]
CMD ["--view", "--port", "8765"]
```

### Running the Container
```bash
docker build -t repopeek:latest .
docker run -d -p 8765:8765 -v $(pwd):/workspace repopeek:latest --repo-path /workspace --view --port 8765
```
Access the viewer at `http://localhost:8765`.
