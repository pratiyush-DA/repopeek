---
id: adr-003-no-distributed-infra
type: decision
title: Prohibition of Distributed Infrastructure in MVP
summary: Prohibit all distributed infrastructure, cloud SaaS deployments, and background
  microservices for the MVP.
status: accepted
tags: [scope, architecture, adr]
affects: ['[[comp-graph]]', '[[con-no-cloud-saas]]', '[[con-no-distributed-graph]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Scope Protection"
depends_on: ['[[con-no-cloud-saas]]', '[[con-no-distributed-graph]]']
---
# ADR-003: Prohibition of Distributed Infrastructure in MVP

## Status
Accepted

## Context
Scope creep in code intelligence tools often introduces microservices, vector databases, message brokers, distributed graph stores, and cloud backend APIs. This creates high maintenance friction, difficult onboarding, and security concerns for developers and agents analyzing proprietary code.

## Decision
Strictly forbid introducing distributed infrastructure or cloud SaaS components into Repopeek MVP. The system must run entirely as a self-contained local Python CLI package.

## Alternatives considered
- **Hosted API / SaaS backend:** Solves central team collaboration, but introduces immense operational complexity, multi-tenancy auth, and security objections.
- **Client-server daemon model:** Allows caching in background process, but introduces socket management, orphan processes, and cross-platform issues.

## Consequences
- **Positive:** Zero deployment friction; runs immediately on any developer workstation or CI container; completely private; easy to test.
- **Negative:** Limited to single-machine resources; cannot share pre-computed graphs between distributed team members without transferring files.

## Notes
[[con-no-distributed-graph]], [[con-no-cloud-saas]], [[moc-decisions]]
