---
name: v1 infrastructure inventory
description: What infra v1 (homeBuild-regulatoryEngine) actually used — raw CloudFormation, not CDK; manual RDS; no CI/CD YAML committed
type: project
---

V1 used raw CloudFormation (infra/aws/cloudformation/stack.yml, 728 lines) — no CDK was ever written.

Key facts:
- ECS Fargate: 3 long-running services (api:8000, frontend:3000, worker) + 1 one-shot migrate task. All 256 CPU / 512 MB.
- RDS: PostgreSQL 17, db.t3.small, single-AZ, provisioned manually via CLI (not in CloudFormation). PostGIS also manual.
- Frontend: Next.js 15 standalone container on Fargate, NOT S3+CloudFront.
- ALB: path-based routing — /api/* → port 8000, everything else → port 3000. HTTPS conditional on ACM cert param.
- ECR: 3 repos (api, worker, frontend), ScanOnPush, no lifecycle policies.
- VPC: 10.0.0.0/16, 2 public subnets only, no NAT Gateway (intentional cost saving).
- No .github CI/CD workflows were committed — only documented in README.
- S3: 1 bucket (source snapshots), manually provisioned, private, versioned.
- Secrets Manager: DB credentials as JSON with async_url + sync_url keys; ECS uses :key:: field extraction syntax.
- NEXT_PUBLIC_API_URL baked at build time (ARG in Dockerfile.frontend) — frontend must rebuild if API URL changes.

**Why:** V2's CLAUDE.md already corrects course by specifying CDK TypeScript as the infra tool.

**How to apply:** When writing v2 CDK stacks, use v1's security group rules, routing logic, and env var patterns as the reference — but don't carry over the pain points (manual RDS, frontend as Fargate container, no lifecycle policies).
