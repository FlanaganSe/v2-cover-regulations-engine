# Architecture Decision Records

## ADR-001: Python + TypeScript Split Architecture
**Date:** 2026-03-22
**Status:** accepted
**Context:** Project requires a regulation/zoning rules engine (computation-heavy, data-pipeline-friendly) alongside a user-facing interface.
**Decision:** Python backend for regulation logic and data processing; TypeScript frontend for the UI layer. AWS for deployment.
**Consequences:** Two separate runtimes to maintain; API contract between them must be well-defined (OpenAPI/REST or GraphQL).
