# Home Building Regulatory Engine

**Status:** Active
**Languages:** Python (backend), JavaScript/TypeScript (frontend)
**Cloud:** AWS preferred, (possibly GCP for geocoding)
**Recommended Tools:** Postgres, PostGIS, Shapely
**AI/ML Frameworks:** TBD

---

## Problem Statement

> For a given parcel, what can I confidently build?

Zoning codes and regulatory documents are distributed across multiple sources and require interpretation to translate general rules into parcel-specific constraints. As projects evolve and new inputs emerge, this understanding must be continuously refined rather than treated as a one-time determination.

The core challenge is producing an **evidence-backed buildability assessment** that synthesizes these sources into:
- A clear statement of what is allowed
- The confidence in that conclusion
- The specific data and rules that support it

When regulations are ambiguous or incomplete, the system should surface reasonable interpretations while clearly distinguishing them from verified constraints.

---

## Business Context

At Cover, every project begins with determining what can realistically be built on a site, yet this process is often slow and manual due to fragmented regulatory research. A reliable buildability assessment would provide faster and more transparent feasibility guidance — helping clients make informed decisions earlier while reducing entitlement surprises.

### Key Impact Metrics

- Reduce regulatory research effort to zero
- Answer buildability questions in real-time as inputs change
- Consistent, cited regulatory answers across parcels

---

## Target User

An Architect or Engineer with knowledge of the code and regulations. They can validate the tool's claims, read a map, understand parcels, and understand technical regulatory language.

---

## Scope: Proof of Concept

- Use latest LLM/AI/ML technology to support the underlying solution
- Geographic scope limited to **residential parcels within the City of Los Angeles**
- Use publicly available parcel, zoning, and regulatory information (or reasonable mock data)
- **Core focus:** regulatory ingestion and synthesis — transforming municipal zoning text into structured, explainable rule fragments for parcel reasoning
- Implement a small, well-reasoned subset of rules/agencies rather than full coverage
- Demonstrate parcel-to-constraints reasoning with explicit citations and confidence signals
- Flexible architecture designed to scale: LA City → LA County → California → beyond
- Prioritize **clarity, traceability, and explainability** over completeness

*More specific resources will be provided before the project starts.*

---

## Functional Requirements (Must-Haves)

1. **Address/APN lookup** — Enter a residential address or APN and get a real-time structured buildability assessment
2. **Zoning and regulatory constraints** — Identify applicable constraints with supporting evidence and citations; clearly distinguish deterministic parcel data from interpretive/inferred conclusions
3. **Confidence and explainability** — Each constraint includes a confidence signal and transparent explanation of how it was derived
4. **Parcel visualization** — Basic visualization of the parcel and any existing buildings
5. **Test coverage** — Tested on a range of provided residential parcels/addresses and building types (Single Family Home, ADU, Guest House, etc.)
6. **User-facing interface** — Target user can interact and easily see outputs
7. **Architecture diagram** — Simple but actionable, illustrating how this could be productionized

---

## Bonus Features

- **Responsive to project inputs** — Output adapts to project state via descriptive or parameterized inputs (e.g., 1 bedroom, 1 bathroom)
- **User feedback loop** — Accept feedback on bad responses to improve future results
- **Chat interface** — Ask follow-up questions about results and the underlying dataset
- **Interactive map** — Translate regulations into visual annotations
- **Geometry generation** — Generate actionable geometry like property setbacks from parcel info and synthesized regulations
- **Admin interface** — Demonstrate the regulatory engine pipeline, adjust system settings