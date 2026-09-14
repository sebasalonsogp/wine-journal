# ADR 0005: Repository foundation and accepted organization

Status: Accepted. Date: September 14, 2026.

## Context

After reviewing the UX, internal module organization, deployment alternatives, long-term needs, and serverless options, the user authorized scaffolding specifically under `repo/` and optionally creating the GitHub repository. This overrides the earlier suggestion to use the parent planning directory as the repository root.

## Decision

Use `repo/` as the Git root, with `apps/web` for Next.js App Router/React/TypeScript and `apps/api` for Python/FastAPI. Adopt the Next.js direction in ADR 0004 and the managed-service/API-ownership direction in ADR 0002. Preserve their original rationale and decision history.

Organize frontend code by workflow and backend code by business domain, with lightweight layers inside modules. Keep the transactional Journal core cohesive; run supporting work separately when its resource or reliability needs require it. Logical domains do not each require independent deployments. Serverless remains a possible execution model, not a mobile-client requirement.

The initial executable foundation is a web startup page and a process-liveness API, with lockfiles, formatting, types, HTTP smoke tests, generated contracts, and CI. Folder markers describe future responsibilities without fake routers, models, data, or generic interfaces. Initialize local Supabase configuration without provisioning cloud services or starting containers. Database migrations, authentication, journal behavior, and the worker remain subsequent implementation slices.

Bring the planning documents and reviewed design references into this repository. These copies become the maintained project documentation; the parent workspace retains the earlier planning artifacts as an archive. Use npm within `apps/web` and uv within `apps/api`; no root JavaScript workspace or monorepo orchestrator is needed.

Create a private `wine-journal` repository under the authenticated personal GitHub account. Public visibility and deployment can be chosen separately.

## Consequences

- A clone contains code, product context, design references, and reproducible setup instructions.
- Native iOS can be added as another client without changing the Journal API boundary.
- The scaffold requires no cloud credentials to build or pass its initial checks.
- Reserved directories are intentional; executable code is added only with working slices.
- The logical data model and unimplemented endpoint designs remain proposals; this decision does not finalize unresolved auth, rating, provider, or media details.
