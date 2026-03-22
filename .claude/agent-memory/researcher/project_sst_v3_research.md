---
name: SST v3 (Ion) fit assessment for regulation engine stack
description: Whether SST v3 is appropriate for FastAPI/ECS/RDS/PostGIS/S3+CloudFront stack; includes deep Python support assessment from March 2026
type: project
---

SST v3 (Ion) was researched twice for this project. The second pass (March 2026) focused specifically
on Python support depth. Combined findings:

**Construct availability:**
- SST v3 has Service, Cluster, Vpc, Postgres, StaticSite constructs — all relevant constructs exist.
- Current npm version is ~3.17.x (as of March 2026).
- PostGIS NOT first-class — requires `CREATE EXTENSION postgis` post-provision; `sst tunnel` makes this easier than v1's workaround.
- SST v3 uses Pulumi (not CDK), state in S3.

**Python support — the honest assessment:**
- Python SDK exists at `sdk/python/` in SST repo, distributed as a git source dependency (NOT on PyPI).
- The `sst` package on PyPI is an unrelated 2013 Selenium testing tool.
- For ECS Fargate containers: Python support is FINE. Resource values are injected as `SST_RESOURCE_*` env vars (JSON), parsed by `from sst import Resource`. No network call, no decrypt needed in container path.
- For Lambda: Python is "community supported" — works but rough. No breakpoints (closed "not planned" Sep 2025, issue #5198). Heavy `cryptography` dep needed for Lambda bundle encryption.
- No Python type generation — unlike TypeScript, there is no `sst-env.d.ts` equivalent. Typos in `Resource.X.y` fail at runtime only.
- `sst dev` + tunnel works for Python containers: `dev.command: "uv run uvicorn ..."` gets `SST_RESOURCE_*` vars injected, tunnel gives VPC access to RDS. Startup timing requires care (issue #5002).
- Migration scripts (Alembic): `sst shell -- alembic upgrade head` injects env vars into shell. No built-in deploy-time hook.
- SST is in MAINTENANCE MODE as of 2025 — core team shifted to OpenCode AI agent. Critical bugs get fixes; new Python features unlikely. (issue #6215)
- Real-world Python + SST v3 production examples: essentially zero found in search.

**Key distinction:** Python Lambda support = second-class. Python container support = fine (language-agnostic black box).

**Why:** User asked for deep Python support assessment after SST was previously recommended.

**How to apply:** If user asks about Python + SST again, the detailed mechanism trace and all trade-offs are in `.claude/plans/research.md`. Short answer: viable for containers, not for Lambda. Maintenance mode is the bigger risk than Python support gaps.
