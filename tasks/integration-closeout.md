# Integration and audit closeout — October 20, 2026

The long-lived access-foundation branch is being integrated before further feature
work. Future changes follow [CONTRIBUTING.md](../CONTRIBUTING.md): focused branches
from current main, small reviewed PRs, passing exact-head CI, and merge commits
that preserve meaningful development history.

Security fixes are isolated commits:

- Certifi 2026.7.22 → 2026.10.19, the audit's patched trust-bundle release.
  [Upstream release](https://github.com/certifi/python-certifi/releases/tag/2026.10.19).
- Pillow 12.3.0 → 13.0.0 in development and the isolated photo decoder. Reviewed
  [security fixes and breaking changes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html);
  current RGB/photo processing passes the existing regression suite. The Docker
  decoder was rebuilt from locked wheel hashes. Historical image evaluation files
  retain their original Pillow version/provenance.
- The Next 16.3.8 lint plugin's vulnerable fast-glob/micromatch/braces chain is
  replaced by a [small scoped adapter](../apps/web/tooling/next-lint-glob/README.md)
  using tinyglobby 0.2.17. This preserves absolute/relative directory matching,
  including Windows cross-drive behavior. No lint rules or audit findings are
  suppressed, and Next is not downgraded.

Local evidence: complete npm and Python dependency audits report no known
vulnerabilities; 511 backend tests pass with local Storage and the rebuilt isolated
decoder. All 37 frontend unit tests, lint, types and formatting pass. Compatibility
tests exercise the actual Next root resolver and prove the internal-link lint rule
still runs. Inverting absolute-path handling fails these tests; restoring the exact
source passes. Remote CI remains the final merge gate.

The user authorized correcting unmerged history from the accidental padstats
identity to sebasalonsogp. The rewrite retains original author/committer dates,
messages and every file tree, and keeps a local backup plus old/new commit mapping
outside the public repository. Future identity is repository-local; global Git
settings and already-published main history are not changed. Use a guarded
force-with-lease only for this authorized branch rewrite, then a normal merge.

Prior checkpoint audit failures are historical evidence, superseded by this
closeout once remote checks pass. Remaining product work (camera UI/device
coverage, broader recognition, deployment and other roadmap tasks) is unchanged.
