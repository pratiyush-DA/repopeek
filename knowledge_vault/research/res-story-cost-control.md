---
id: res-story-cost-control
type: research
title: Story Generation Cost Control and Optimization Strategies
summary: Best practices for managing LLM costs via deterministic templates, content-hash
  caching, bottom-up summarisation, and verifiers.
status: completed
tags: [research, llm, cost-control, caching, summarization]
code_refs: []
depends_on: ['[[plan]]']
affects: ['[[adr-007-story-cost-cascade]]', '[[comp-enrichment]]']
last_verified: 2026-10-03
---
# Story Generation Cost Control and Optimization Strategies

## Problem Statement
Generating natural language summaries and stories across an entire repository can consume millions of tokens if done naively (e.g. sending entire source files to a frontier model). To make RepoPeek economically viable on large repositories, LLM utilization must be strictly minimized and governed.

## Optimization Techniques

### 1. Deterministic Skeleton First (Zero Cost)
Up to 70% of codebase symbols (getters, setters, `__repr__`, boilerplate dataclasses, one-line wrappers, standard configuration constants) have obvious semantics directly extractable from AST facts.
- **Rule:** If docstring or signature + call targets explain the function without ambiguity, construct a deterministic story template without an LLM call.

### 2. Content-Hash Invalidation Cache (O(Changes), Not O(Repo))
- **Cache Key:** `hash(normalized_source + child_story_hashes + prompt_version + model_tier)`
- **Behavior:** Unchanged code is never re-summarized. Incremental runs achieve near 100% cache hit rates. The cache is persisted alongside the graph artifacts.

### 3. Hierarchical (Bottom-Up) Map-Reduce Summarisation
- **Mechanism:** Method stories are combined to form class stories; class/function stories are combined to form module stories; module stories form package stories.
- **Token Savings:** The LLM receives compact child summaries (50 tokens each) and AST facts rather than thousands of lines of raw source code, cutting input token volume by 80–90%.

### 4. Cheap-Model Structured Summary with Constrained Decoding
- **Model Tiers:** Use fast, high-throughput models (e.g. `llama-3.1-8b-instant` or `gpt-oss-20b` via Groq) constrained to a strict JSON schema (story string <= 30 words, confidence rating).
- **Prompt Caching:** Place static instructions, schema descriptions, and few-shot examples at the start of the prompt to trigger Groq's automatic 50% prompt-cache discount.

### 5. Strong Model Escalation (Hotspots Only)
- Frontier/strong models are reserved exclusively for:
  - Top 5% high fan-in architectural hubs.
  - Nodes where the initial story had low confidence (<0.6).
  - Nodes that failed the anti-hallucination verifier.

### 6. Anti-Hallucination Fact Verifier
- An automated AST-based fact checker validates generated stories:
  - Any story claiming a database read, external call, or exception that is absent from the node's AST facts is rejected and downgraded to the deterministic template.

## Strategy Summary
Adopted as [[adr-007-story-cost-cascade]].
