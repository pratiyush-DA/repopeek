---
id: adr-012-secrets-and-privacy
type: decision
title: Secret Handling, Client-Side Redaction, and Privacy Protections
summary: Enforce strict environment-only secrets, client-side secret/PII redaction
  before LLM dispatch, and complete offline capability.
status: accepted
tags: [security, privacy, secrets, redaction, adr]
code_refs: []
depends_on: []
affects: ['[[con-local-execution]]', '[[moc-decisions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA76.2 & \xA76.3"
---
# ADR-012: Secret Handling, Client-Side Redaction, and Privacy Protections

## Status
Accepted

## Context
Codebases frequently contain proprietary business logic, hardcoded tokens, internal IP, or sensitive configuration values. A tool that analyzes local repos must never inadvertently transmit secrets to cloud LLM providers or write unredacted credentials to output graph files.

## Decision
1. **Secret Storage:** All API keys (`GROQ_API_KEY`, etc.) are sourced strictly from environment variables. A template `.env.example` is provided, and `.env` is permanently git-ignored. Secret scanning (e.g. `gitleaks`) is integrated into pre-commit and CI.
2. **Client-Side Redaction:** Prior to any snippet being dispatched to an LLM for story enrichment, a local redaction filter masks:
   - High-entropy strings, JWTs, private keys, API keys.
   - Database connection strings and credentials.
   - PII patterns (emails, tokens).
3. **Graph Protection:** The Config/Environment lens records secrets **by name only** (e.g. `DB_PASSWORD`), never capturing their runtime values.
4. **Offline Mode:** Running with `--offline` completely disables all outbound HTTP network calls, relying 100% on the deterministic tier.

## Consequences
- Zero risk of credential exfiltration; enterprise-grade compliance.

## Notes
[[con-local-execution]], [[moc-decisions]]
