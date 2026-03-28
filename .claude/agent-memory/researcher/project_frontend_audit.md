---
name: project_frontend_audit
description: Complete frontend implementation inventory as of March 2026 — components, state, API, types, design system, tests
type: project
---

Full audit documented at `.claude/plans/research-frontend.md` (March 2026).

Key facts that shape future work:

**Architecture:** SPA, no router, single App.tsx with all state. ViewState enum ("home"|"loading"|"error"|"assessment") drives sidebar content.

**Components:** App, SearchBar, Map, AssessmentPanel (+ 9 private sub-components), HomePanel (+ 4 private sub-components), ConfidenceBadge. All in `frontend/src/components/`.

**Design system:** Tailwind v4 CSS-first only. No component library installed (shadcn/ui is planned per stack.md but not present). No design tokens. Blue accent on gray/white base. Brand purple only in favicon.svg.

**State:** All local useState in App.tsx. No context, no store. localStorage for recent searches (key: "recentParcelSearches", max 5).

**API client:** Raw fetch in `src/lib/api.ts`. Base URL from VITE_API_URL env var. Three endpoints: GET /api/home, GET /api/parcels/search, GET /api/parcels/{ain}.

**Types:** `src/types/assessment.ts` and `src/types/home.ts` mirror backend Pydantic models exactly. Contract verified against `docs/openapi.json`.

**Tests:** App.test.tsx (4 integration tests), recentSearches.test.ts (2 unit tests). Map is mocked. SearchBar, AssessmentPanel, HomePanel, useParcelSearch, mapStyle have no tests.

**Key gaps for redesign:** No URL routing, fixed w-96 sidebar (not responsive), no map click handler, no loading skeletons, @protomaps/basemaps installed but unused (OSM raster used instead), icons.svg dead asset, no brand color in UI.

**Why:** Sean is planning a complete UX redesign. This audit is the foundation for that plan.

**How to apply:** When discussing frontend work, reference this audit for current component shapes, props, and constraints.
