# Wine Journal web

Next.js App Router with React, TypeScript, and Tailwind. The root page is a startup screen using the reviewed Stitch tokens. Product routes and feature folders are reserved; no sign-in, capture, or journal workflow is implemented yet.

Requires Node.js 24 LTS and npm. From this directory:

```sh
npm ci
npm run dev
```

Open `http://localhost:3000`. No environment variables are required yet. `.env.example` identifies the future public API configuration.

```sh
npm run format:check
npm run lint
npm run typecheck
npm run build
npm run start
```

Thin files in `src/app` compose screens from `src/features`. Shared UI belongs in `src/components`; infrastructure belongs in `src/lib`. Business rules and private data authorization live in FastAPI. Add TanStack Query, Supabase session handling, form libraries, and selected UI primitives with the first feature that needs them.

Generate API types with `npm run generate:api` after exporting the backend schema. Do not edit `src/lib/api/schema.d.ts` manually. See [the root README](../../README.md) for the complete repository map and setup.
