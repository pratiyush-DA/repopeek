---
id: con-no-cloud-saas
type: constraint
title: Prohibition of Cloud SaaS and Multi-Tenant Architecture
summary: Repopeek must remain a standalone developer utility and never be structured
  as a cloud SaaS or multi-tenant service.
status: active
tags: [constraint, scope, architecture]
affects: ['[[adr-003-no-distributed-infra]]', '[[comp-cli]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Scope Protection"
depends_on: ['[[adr-003-no-distributed-infra]]']
---
# Prohibition of Cloud SaaS and Multi-Tenant Architecture

## Rule
Repopeek must NEVER be turned into a cloud SaaS platform, hosted multi-tenant API, or remote subscription service. All architecture and design decisions must serve single-user or single-agent local developer workflows.

## Rationale
Prevents severe scope bloat, user authentication complexity, multi-tenant data segregation liabilities, and billing infrastructure overhead during the MVP.

## What it prohibits
- Building multi-tenant authentication, user management, or billing tiers.
- Requiring remote API servers to orchestrate local repo analysis.
- Exposing unauthenticated network ports or services.

## Enforcement
- Architectural verification during planning and PR review.

## Related
[[adr-003-no-distributed-infra]], [[moc-decisions]]
