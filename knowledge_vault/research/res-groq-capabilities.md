---
id: res-groq-capabilities
type: research
title: Groq API Capabilities, Pricing, and Architecture
summary: Technical specifications for Groq inference platform, OpenAI compatibility,
  structured outputs, and prompt caching.
status: completed
tags: [research, groq, llm, api, structured-outputs]
code_refs: []
depends_on: ['[[plan]]']
affects: ['[[adr-006-llm-provider-abstraction]]', '[[comp-enrichment]]']
last_verified: 2026-10-03
---
# Groq API Capabilities, Pricing, and Architecture

## Overview & Endpoint Specification
- **Base URL:** `https://api.groq.com/openai/v1`
- **Compatibility:** Fully compatible with OpenAI Python SDK / Chat Completions API.
- **Authentication:** `Bearer $GROQ_API_KEY` via HTTP header.
- **Hardware Architecture:** Language Processing Units (LPUs) offering low TTFT (Time-to-First-Token) and 500–1000+ tokens per second.

## Key Technical Features

### 1. Structured Outputs
- **Mechanism:** Constrained decoding at the engine level guarantees response conforms exactly to a provided JSON schema.
- **Usage:**
  ```python
  response = client.chat.completions.create(
      model="llama-3.3-70b-versatile",
      messages=[...],
      response_format={
          "type": "json_schema",
          "json_schema": {"name": "NodeStory", "strict": True, "schema": StorySchema},
      },
  )
  ```
- **Guarantees:** Eliminates malformed JSON errors and invalid field keys.

### 2. Automatic Prompt Caching
- **Mechanism:** Server-side prefix matching caches static instructions and schema templates.
- **Economics:** 50% discount on input tokens for cache hits; cached tokens do not count against rate limits.
- **Optimization Rule:** In prompts, keep system instructions and JSON schema static at the prompt prefix, appending per-node dynamic source code at the end.

### 3. Asynchronous Batch API
- **Discount:** Approximately 50% discount compared to real-time rates.
- **Turnaround:** Asynchronous completion within 24 hours via JSONL file submission.
- **Application:** Ideal for bulk first-time codebase indexing runs where real-time interactive response is not required.

### 4. Available Models & Abstract Tier Mapping
To maintain provider independence, models are mapped to abstract tiers in `repopeek.toml`:
- **Fast Tier:** `llama-3.1-8b-instant` / `openai/gpt-oss-20b` (leaf function summaries, high throughput).
- **Balanced Tier:** `llama-3.3-70b-versatile` (class and module aggregation).
- **Strong Tier:** `openai/gpt-oss-120b` or frontier models (cross-module business process discovery, high fan-in hotspots).

## Architectural Rule
No model names or URLs will be hardcoded in application logic. All model references must be resolved dynamically through `RepopeekConfig` tiers.
