# Wine Journal web

Next.js App Router with React, TypeScript, and Tailwind. Email-code sign-in opens a real private journal using the reviewed Stitch tokens. Guests can start manual capture at `/capture`, sign in to save, and reopen persisted wines/history under `/my-wines`. Browse and Guides remain placeholders for future catalog and editorial content.

Requires Node.js 24 LTS and npm. From this directory:

```sh
npm ci
npm run dev
```

Open `http://localhost:3000`. Guest pages work without configuration; sign-in requires the generated ignored environment files, local Supabase and FastAPI. Follow [local setup](../../supabase/README.md). `.env.example` contains names and safe defaults only.

```sh
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm run start
```

Thin files in `src/app` compose screens from `src/features`. Shared UI belongs in `src/components`; infrastructure belongs in `src/lib` and does not import features. Business rules and private data authorization live in FastAPI. Supabase refresh credentials stay in HTTP-only cookies; short-lived access tokens live in memory. TanStack Query caches account-scoped read models, never tokens. Session-storage capture drafts contain product fields and a retry key, are bound to a verified owner after sign-in, and clear on sign-out. See [browser tests](tests/e2e/README.md) and [authentication](../../docs/authentication.md).

Generate API types with `npm run generate:api` after exporting the backend schema. Do not edit `src/lib/api/schema.d.ts` manually. See [the root README](../../README.md) for the complete repository map and setup.
