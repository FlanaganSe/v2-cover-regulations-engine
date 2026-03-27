# MVP Implementation Plan

Date: 2026-03-26
Plan basis: `.plans/research.md`, `docs/requirements.md`, `docs/DATA_SOURCES.md`, `docs/CONSOLIDATED_RESEARCH.md`, `docs/decisions.md`

## Contract

### 1. Problem

Build a demo-grade MVP for the LA residential regulation engine that can resolve a parcel by address or APN, determine core zoning/buildability facts deterministically, explain those facts clearly, and deploy on an AWS-aligned path without over-engineering the system.

### 2. Requirements

- Support LA City residential parcels only.
- Support Original Code / Chapter 1 zones only.
- Resolve parcels by address or APN.
- Return evidence-backed parcel assessment with:
  - zoning designation
  - parsed development standards
  - overlay warnings
  - citations/source references
  - deterministic confidence level
  - optional LLM plain-English explanation
- Show parcel/building/zoning context on a map.
- Handle ambiguity and unsupported cases gracefully.
- Keep ingestion isolated from runtime application concerns.
- Keep APIs and schemas explicit and extensible.
- Keep the MVP easy for an agent orchestrator to implement milestone by milestone.
- Include testing, linting, typing, deployment, CI, and manual setup considerations.

### 3. Acceptance Criteria

- A user can search by address or APN and retrieve a parcel detail view.
- The backend returns parcel facts, zoning facts, development standards, overlays, confidence, citations, and data freshness metadata in one response.
- The deterministic rules engine handles the documented MVP zone classes and returns unsupported status when it cannot answer safely.
- The frontend renders a usable demo experience with map, parcel identity, standards, warnings, and explanation.
- The app can be run locally with Docker-backed dependencies.
- The app can be deployed through an AWS-targeted path with documented manual setup.
- CI verifies lint, type safety, and tests for both backend and frontend.
- Ingestion is runnable independently, resumable, and validated before the app depends on it.

### 4. Non-goals

- Full citywide entitlement analysis beyond the documented residential MVP
- Deep specific-plan or HPOZ rule modeling
- Full code parsing of LAMC or ICC building code
- Nationwide or multi-jurisdiction abstractions
- Production-grade auth, billing, or enterprise governance
- Overbuilt data-platform patterns such as raw/stage/core/publish schemas

### 5. Constraints

- The repo currently contains documentation only; all implementation scaffolding must be created.
- Repo ADRs and project docs point to AWS deployment, even though one stack note still references Railway/Vercel for PoC. This plan treats AWS as the target and keeps the app portable.
- Do not depend on the LLM for deterministic calculations or confidence scoring.
- Do not expand scope to unsupported parcel categories when the safe behavior is to mark them unsupported.
- Keep milestones independently verifiable and committable.

## Implementation Plan

### 1. Summary

Build the MVP in six milestones, ordered to reduce risk:

1. foundation and contracts
2. ingestion and data verification
3. deterministic backend parcel assessment
4. LLM explanation and guardrails
5. frontend MVP experience
6. AWS deployment, CI/CD, and demo hardening

This ordering front-loads the highest-risk unknowns: data quality, schema shape, parcel resolution, and zoning-rule correctness. The frontend and LLM only land after the deterministic engine and seed data are proven.

### 2. Current State

- No backend code exists.
- No frontend code exists.
- No infra code exists.
- No CI exists.
- No schema, migrations, or ingestion code exist.
- Strong documentation exists for scope, data sources, architecture direction, and risks.

### 3. Files to Change

These are the likely existing files that should be updated during implementation:

- `docs/decisions.md`
- `CLAUDE.md`
- `docs/requirements.md` only if scope language must be clarified after milestone delivery review

### 4. Files to Create

Planned project structure:

- `backend/pyproject.toml`
- `backend/Dockerfile`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/routers/parcels.py`
- `backend/app/models/*.py`
- `backend/app/schemas/*.py`
- `backend/app/services/parcel_service.py`
- `backend/app/services/rules_engine.py`
- `backend/app/services/llm_service.py`
- `backend/app/data/zone_rules.py`
- `backend/tests/**`
- `backend/scripts/create_tables.py`
- `backend/scripts/ingest.py`
- `backend/scripts/verify_data.py`
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/vercel.json` only if a non-AWS fallback preview path is retained
- `frontend/src/**`
- `infra/cdk/**`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `docker-compose.yml`
- `.plans/runbooks/*.md` for seed/deploy/demo operations

### 5. Milestone Outline

#### Milestone 1: Foundation and Contracts

Goal:
- Create the runnable skeleton, local infrastructure, shared contracts, and quality gates before feature work starts.

Scope:
- scaffold backend, frontend, and infra directories
- add Docker Compose with PostGIS and Martin
- define backend config, database wiring, and placeholder routes
- define shared API response shape and frontend types
- add lint, format, test, and typecheck commands
- add baseline CI for backend and frontend

Deliverables:
- local bootable workspace
- documented env vars and startup steps
- initial OpenAPI contract and TypeScript response types
- health endpoint and placeholder parcel endpoint
- CI running lint/type/test placeholders successfully

Verification:
- `docker compose up` brings up DB and Martin
- backend and frontend install cleanly
- `pytest`, `ruff check .`, `mypy .`, and `pnpm ci` all run with baseline green status

Commit boundary:
- platform skeleton only, no real ingestion or zoning logic

Agent prompt:
```text
Build the initial project skeleton for the LA regulation engine MVP. Create backend, frontend, and infra directories; local Docker Compose with PostGIS and Martin; baseline FastAPI and React/Vite apps; shared response contracts; and CI checks for lint, types, and tests. Keep the implementation minimal but runnable. Do not implement business logic yet beyond placeholder health and parcel endpoints.
```

#### Milestone 2: Ingestion and Data Verification

Goal:
- Prove that the required seed data can be pulled, normalized, loaded, indexed, and validated independently of the app.

Scope:
- create isolated ingestion scripts under `backend/scripts/`
- create DDL and indexes for all MVP tables
- implement ArcGIS pagination, checkpointing, provenance tracking, and geometry normalization
- load parcels, zoning, overlays, boundaries, community plans, GPLU, and demo buildings
- implement data verification scripts and sample query checks
- select and document demo/test parcel categories after data lands

Deliverables:
- idempotent table creation script
- resumable ingestion script
- verified PostGIS tables with indexes
- `ingest_metadata` populated
- runbook for initial seed and reseed

Verification:
- seed completes against the documented sources
- geometry validity and CRS checks pass
- row counts roughly match documented expectations
- sample parcel QA confirms LA City filtering and zoning joins work

Commit boundary:
- data exists locally and can be verified without any UI work

Agent prompt:
```text
Implement the isolated ingestion layer for the MVP. Create PostGIS tables and indexes, build resumable ArcGIS ingestion scripts with checkpoints and provenance, normalize geometry to EPSG:4326, and add verification scripts for row counts, geometry health, and sample parcel joins. Keep ingestion separate from runtime app code and optimize for reproducible demo seeding.
```

#### Milestone 3: Deterministic Backend Parcel Assessment

Goal:
- Ship the core backend behavior without any LLM dependency.

Scope:
- implement address/APN search
- implement parcel detail endpoint that performs spatial joins
- implement zone string parsing
- implement curated residential rule pack
- compute development standards and deterministic confidence
- surface unsupported and ambiguous states explicitly
- include citations, source metadata, and data freshness in responses

Deliverables:
- search endpoint
- parcel detail endpoint
- deterministic rules engine
- structured parcel assessment schema
- backend tests covering supported and unsupported parcel categories

Verification:
- test fixtures exercise R1, RE/RS, RD/R3, overlay, split-zone, outside-city, and unsupported cases
- no LLM needed for green backend tests
- API returns stable structured output in one request per parcel detail load

Commit boundary:
- backend can power the demo with deterministic facts only

Agent prompt:
```text
Implement the deterministic backend parcel assessment flow. Add parcel search by address/APN, spatial joins for zoning and overlays, zone-string parsing, curated residential rule evaluation, deterministic confidence logic, and a single parcel detail response that includes citations and data freshness metadata. Unsupported cases must return explicit scope/status results instead of speculative answers.
```

#### Milestone 4: LLM Explanation and Guardrails

Goal:
- Add explanation quality without letting the LLM control the decision.

Scope:
- implement OpenAI client integration using Responses API
- keep model name configurable
- use schema-constrained output for explanation payload
- pass only structured deterministic facts and citation whitelist into the prompt
- add fallback behavior when LLM is unavailable
- add tests around prompt assembly, response validation, and failure fallback

Deliverables:
- `llm_service.py`
- config-driven model selection
- deterministic fallback path with `llm_available=false`
- prompt/citation guardrails

Verification:
- backend tests confirm failed LLM calls do not break parcel assessments
- output never changes deterministic standards/confidence fields
- citations in explanation come only from known references

Commit boundary:
- explanation layer is optional and safely degradable

Agent prompt:
```text
Add the LLM explanation layer to the backend using the OpenAI Responses API with structured output validation. The model must explain deterministic parcel facts, not decide them. Keep the model slug configurable, enforce citation whitelisting, and return a deterministic fallback response whenever the LLM is unavailable or invalid.
```

#### Milestone 5: Frontend MVP Experience

Goal:
- Deliver the demo UX once the backend contract is stable.

Scope:
- implement search UI with debounce and APN-aware behavior
- implement map with parcel, zoning, building, and overlay layers
- implement parcel assessment panel with standards, warnings, citations, and confidence
- surface unsupported states, no-result states, and LLM fallback states clearly
- keep the UI flexible for future additions without introducing frontend over-abstraction

Deliverables:
- usable search-to-assessment flow
- map-centered parcel context
- clear evidence and caveats presentation
- frontend test coverage for core flows and state handling

Verification:
- user can search, select a parcel, and understand the result without reading raw JSON
- UI makes source citations and uncertainty apparent
- frontend tests cover loading, error, unsupported, and successful states

Commit boundary:
- complete demo UX against local seeded data

Agent prompt:
```text
Implement the frontend MVP on top of the stable parcel detail API. Build the search experience, map layers, parcel assessment panel, citations, confidence presentation, and graceful unsupported/error states. Prioritize clarity and evidence display over breadth of features, and keep the structure extensible for later admin/chat additions.
```

#### Milestone 6: AWS Deployment, CI/CD, and Demo Hardening

Goal:
- Make the MVP deployable and operable with a documented AWS path and safe demo workflow.

Scope:
- define AWS infrastructure in CDK
- deploy backend service, Martin service, PostGIS database, and static frontend
- wire secrets and environment configuration
- add GitHub Actions for CI and deployment
- add smoke checks and runbooks for seed/deploy/demo reset
- validate end-to-end behavior in deployed environment

Recommended AWS shape:
- frontend: S3 + CloudFront
- backend: ECS Fargate service
- Martin: ECS Fargate service
- database: RDS PostgreSQL with PostGIS-enabled image/extension strategy accepted by the team

Deliverables:
- CDK app and environment docs
- CI workflow
- deploy workflow
- smoke test checklist
- operator runbook for initial seed, reseed, rollback, and demo prep

Verification:
- one documented deployment path works end to end
- deployed app can serve parcel search, parcel detail, map tiles, and LLM-backed explanation
- manual steps and secrets are documented clearly enough for another operator to reproduce

Commit boundary:
- MVP is locally and remotely demoable

Agent prompt:
```text
Implement the AWS deployment path for the MVP using CDK and GitHub Actions. Deploy the static frontend, FastAPI backend, Martin tile service, and PostGIS-backed database with documented secrets, smoke checks, and rollback steps. Keep the application architecture portable, but make AWS the default supported deployment target because it matches the repo ADRs.
```

### 6. Testing Strategy

- Backend unit tests:
  - zone-string parsing
  - rules lookup
  - confidence computation
  - response serialization
- Backend integration tests:
  - parcel search
  - parcel detail spatial joins
  - unsupported/out-of-scope responses
  - LLM fallback behavior
- Ingestion verification:
  - row counts
  - geometry validity
  - CRS normalization
  - sample parcel spot checks
- Frontend tests:
  - search interactions
  - loading/error/unsupported states
  - assessment rendering
- Deployment smoke checks:
  - `/health`
  - sample parcel detail query
  - tile endpoint response
  - frontend load against deployed APIs

Quality gates for every milestone after Milestone 1:

- backend: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`
- frontend: `pnpm ci`
- any milestone touching ingestion must run verification scripts against the current seed

### 7. Migration and Rollback

Because the repo is greenfield, rollback is mostly about preserving known-good seeds and deployable versions.

Plan:

- keep schema creation idempotent and additive during MVP buildout
- avoid destructive data migrations until the first stable demo seed exists
- treat each seed run as versioned operational state with provenance and documented source dates
- retain a previous app deploy artifact and prior DB snapshot before any schema-affecting release
- allow the frontend/backend to run with deterministic-only mode if the LLM path is broken
- if a new seed introduces regressions, revert to the prior DB snapshot or prior raw export and reseed

### 8. Manual Setup Tasks

- Create AWS accounts/environments or confirm the target AWS account and region.
- Bootstrap CDK for each deployment environment.
- Decide how PostGIS is provisioned on AWS and document that choice in `docs/decisions.md`.
- Create OpenAI project credentials and store the API key in the chosen secret manager.
- Create GitHub Actions secrets or configure GitHub OIDC for AWS deploys.
- Curate the initial `zone_rules` pack from:
  - zoning summary PDF
  - ZA Memo 143
  - selective zoning code manual references
- Choose the demo building seed neighborhoods or bbox inputs.
- Run the first seed manually and capture row counts plus retrieval dates.
- Select and document test/demo parcels after ingestion.
- Configure CORS origins for local and deployed environments.
- Create a demo operator runbook covering:
  - seed
  - reseed
  - deploy
  - rollback
  - smoke test

### 9. Risks

- AWS deployment complexity is higher than the research doc's lower-risk Railway/Vercel path. Mitigation: keep app design portable and isolate infra as the final milestone.
- PostGIS on AWS must be validated early enough that infra does not become the late blocker. Mitigation: decide the exact AWS PostGIS approach during Milestone 1 and record it.
- The rule pack is manual and therefore error-prone. Mitigation: narrow supported zones and require citations/tests per rule.
- ArcGIS source instability can break first-time seed runs. Mitigation: checkpointing, verification scripts, and optional raw export cache for critical layers.
- Unsupported parcel patterns will appear. Mitigation: explicit unsupported responses are part of the MVP, not a failure mode.
- LLM model slugs and behavior can change. Mitigation: keep model configurable and validate schema-constrained outputs.
- Frontend polish can sprawl. Mitigation: postpone bonus features until the core search -> assess -> map loop is done.

### 10. Open Questions

- Which exact AWS pattern should be used for PostGIS in this repo: RDS PostgreSQL with approved PostGIS support, containerized PostGIS on ECS/EC2 for the demo, or another accepted team standard?
- Should the initial deployed demo seed all LA City parcels immediately, or should the first remote environment use a reduced seed and promote to full LA City once verified?
- Are hillside-related flags required for the first demo, or can they remain a clearly documented stretch item?
- Should deployment workflows auto-run ingestion in non-prod, or should ingestion remain a manual operator action to reduce accidental source/API load?
