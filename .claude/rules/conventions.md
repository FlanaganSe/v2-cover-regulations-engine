# Conventions

## Backend (Python)
- Test files: `test_foo.py` in `tests/` mirroring `src/` structure
- `__all__` for public API exports
- Type hints on all public functions
- Ruff handles formatting — do not hand-format

## Frontend (TypeScript)
- Co-located tests: `foo.ts` → `foo.test.ts`
- Named exports over default exports
- Explicit return types on all public functions
- Prettier handles formatting — do not hand-format

## Shared
- Domain terminology: prefer "regulation", "zone", "parcel", "permit" over generic names
- No magic strings — use enums or const maps for regulation codes and zone types
