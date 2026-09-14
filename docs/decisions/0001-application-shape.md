# ADR 0001: Python modular monolith with a React web client

Status: Previous proposal; frontend recommendation replaced by [ADR 0004](0004-nextjs-and-portfolio-budget.md). Date: September 14, 2026. The modular Python backend recommendation remains current.

## Context

The user prefers Python, has designed a private web journal, and expects future iOS, public reviews, and collaboration. The initial discussion suggested Next.js, but no application exists. A solo portfolio project needs understandable boundaries and manageable operations.

## Decision

Recommend FastAPI as the sole owner of application behavior, with feature modules sharing Postgres and transaction boundaries. Use React/TypeScript with Vite, React Router, and TanStack Query for the first web client. Generate the transport contract from FastAPI OpenAPI. Build features as complete UI/API/data slices.

## Alternatives and consequences

- **Next.js + FastAPI:** stronger integrated rendering options for future public pages; introduces another server framework if used dynamically. Prefer it now if public SEO becomes a first-release requirement. Moving later is possible but has real routing/rendering/auth integration cost.
- **All-TypeScript full-stack app:** reduces language boundaries; gives up the user's Python backend preference. Not the recommendation for this project.
- **Django:** a sound Python alternative, especially if built-in administration becomes central. This API-first client experience already uses managed auth; FastAPI fits the narrower API role. Neither is universally more professional.
- **Microservices:** unnecessary operational and distributed-transaction costs for the current scope. A media worker can use the same codebase without dividing business services.

A Vite SPA needs deliberate route loading, caching, and a later rendering decision for public discovery. This is an accepted proposed tradeoff, not a claim that Vite includes SSR. [React guidance](https://react.dev/learn/build-a-react-app-from-scratch)

Revisit when public SEO is in scope, or measured deployment/workload requirements justify another application shape. Full structure: [architecture](../architecture.md).
