# ADR 0004: Next.js frontend and a lean portfolio budget

Status: Accepted through [ADR 0005](0005-repository-foundation.md), replacing the frontend recommendation in ADR 0001. Date: September 14, 2026.

## Context

The user asked for actual Vite savings and migration effort, emphasizing future public features, maintainability, industry-standard tools and minimal spend. They also clarified that commercial licensing work should wait and iPhone media formats must be supported. No frontend exists, so changing the proposal now has no application migration cost.

## Decision

Recommend Next.js App Router with React and TypeScript, keeping FastAPI, SQLAlchemy/Alembic and Supabase. Next owns routes, layouts and web rendering. FastAPI owns journal authorization, transactions and business behavior. Fetch private journal data from the browser through the verified-token API; use public server rendering where it serves wine pages/guides. Do not add a parallel Next business API or React Router.

Use a normal Next deployment, initially on a compatible free personal tier such as Vercel Hobby. Arbitrary private IDs created after build make pure static export a poor fit for the planned path structure. Keep all framework-specific files thin around feature components.

Prioritize local/free operation and curated demo data where useful. Defer commercial licensing research and paid procurement to a later distribution/commercial decision; basic access and free quotas are checked as integrations are selected. Include HEIF/HEIC and HEVC compatibility in the media slice with bounded input, worker conversion, compatible derivatives and real-phone checks.

## Alternatives and consequences

- **Vite + React Router:** valid for the interactive MVP, simpler static deployment and fewer rendering concepts. It has no guaranteed dollar advantage when both frontends fit a free tier. Routing, caching and server-rendering work remain if adopting Next later.
- **Next from the start:** modest additional framework learning and server/client/cache discipline; provides a coherent route/rendering path for the already-envisioned public product. Next is not necessary for recommendations or native iOS; those depend on backend features and an independent API.
- **Static-export Next:** possible for known paths or a redesigned SPA route scheme, but does not automatically support arbitrary new dynamic paths. Avoid changing URLs around that deployment limitation.

An eventual Vite migration preserves much React UI and the Python backend, but needs build/env changes, route/link/layout changes and tests; adopting server-rendered public pages also changes data loading, metadata and caching. Estimate several focused days for a small finished MVP, not a measured promise or a reason to build that migration now. Both software choices can be free; actual runtime and learning costs vary.

Backend architecture remains a modular monolith with feature-oriented lightweight layering. Review [architecture.md](../architecture.md) for the updated folder tree, runtime boundaries and media approach.

## Sources

- [Next migration guide](https://nextjs.org/docs/app/guides/migrating/from-vite)
- [Next static exports](https://nextjs.org/docs/app/guides/static-exports)
- [Vercel Hobby](https://vercel.com/docs/plans/hobby)
- [React framework guidance](https://react.dev/learn/creating-a-react-app)
- [Apple HEIF/HEVC media](https://support.apple.com/en-us/116944)
