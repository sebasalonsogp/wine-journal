# Next.js runtime security update — October 23

The dependency audit now flags Next 16.3.8 for three advisories published to the
GitHub advisory database October 22. Earlier green audits are dated evidence,
not a permanent claim. Upgrade the runtime to exact version **16.4.3** and
regenerate the npm lockfile; no audit exclusion or forced bulk update is used.

Upstream fixes first shipped in
[16.4.1](https://github.com/vercel/next.js/releases/tag/v16.4.1):

- [Image Optimization SVG RCE](https://github.com/advisories/GHSA-2464-fhr4-w9xw).
- [App Router Server Action denial of service](https://github.com/advisories/GHSA-p3m5-59mp-jv5r).
- [Typed-array cache-function RCE](https://github.com/advisories/GHSA-673q-mjm6-r5xr).

The application currently has no `next/image`, `use server` or `use cache`
usage in its source; this narrows known feature exposure but does not justify
retaining the flagged framework. This is a dependency finding, not evidence of
an exploited deployment or leaked secrets.

Reviewed the [16.4 release](https://nextjs.org/blog/next-16-4) and
[16.4.2](https://github.com/vercel/next.js/releases/tag/v16.4.2)/
[16.4.3](https://github.com/vercel/next.js/releases/tag/v16.4.3) changes, including
Turbopack fixes. The lock diff changes only Next, its env/compiler packages and
its Sharp minimum requirement (the resolved Sharp was already sufficiently new).
Node's >=20.9 requirement and React 19 support remain compatible with the project.
No new runtime flags or framework features are enabled.

The lint config/plugin stays at 16.3.8 with the existing narrowly scoped glob
adapter. Its compatibility tests exercise the real plugin; changing it is not
necessary to resolve these runtime advisories. No unrelated dependencies change.

The production build/type checking and npm audit pass locally after the update.
The complete existing CI gates must pass for this exact commit before merge.
Tasting guidance is a separate dependent feature PR, not part of this update.
