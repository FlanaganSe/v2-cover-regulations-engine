# v2-regulation-engine

Regulation and zoning compliance engine — Python backend, TypeScript frontend, AWS-deployed.

## Commands

### Backend (Python)
```bash
uv run dev                              # Local dev server
pytest                                  # Unit tests
ruff check . && ruff format --check .  # Lint + format check
mypy .                                  # Type check
```

### Frontend (TypeScript)
```bash
pnpm dev          # Local dev
pnpm test         # Unit tests
pnpm ci           # Typecheck + lint + test
```

### Infrastructure (AWS)
```bash
cdk deploy        # Deploy to AWS
cdk diff          # Preview changes
cdk synth         # Synthesize CloudFormation
```

## Rules

@.claude/rules/conventions.md
@.claude/rules/stack.md
@.claude/rules/immutable.md

## Workflow

`/discover` → `/research` → `/plan` → `/milestone` → `/complete`

## Escalation Policy

If a test, lint, or typecheck fails 3 times after attempted fixes, STOP and report what you've tried.
If a plan step is ambiguous, ask before implementing.
