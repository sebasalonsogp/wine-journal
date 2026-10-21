# Temporary Next lint glob adapter

The pinned `@next/eslint-plugin-next@16.3.8` imports `fast-glob` only in
`dist/utils/get-root-dirs.js`, calling `globSync(string, {onlyDirectories: true})`.
Its dependency chain includes unpatched `braces` advisory
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).

This private local package replaces that specific call with maintained
[tinyglobby](https://github.com/SuperchupuDev/tinyglobby), pinned to 0.2.17. The
package declares its real name; it is not a relabeled patched release of braces.
The direct development dependency makes npm's local-file reference reproducible;
the override is scoped to the exact Next plugin version. No postinstall mutation,
audit exception, disabled lint rule or Next downgrade is used.

Two compatibility differences require this adapter rather than a direct alias:
absolute patterns must produce absolute paths (including Windows cross-drive
paths), and literal directories must not expand recursively. Directory suffixes
are normalized to fast-glob's output shape. Unsupported calls fail explicitly.

`tests/unit/lint-glob.test.ts` exercises the actual Next plugin root resolver with
default, relative, absolute, array, brace and Windows-separated patterns. It also
checks that the existing ESLint configuration still reports an invalid internal
HTML link after discovering a fixture's pages. All existing lint rules remain on.

Before changing the Next plugin version, inspect all its glob call sites. Remove
this override, direct dependency, adapter and compatibility tests when upstream
provides a safe implementation, then regenerate the lockfile and run lint, tests,
build and the complete npm audit. Never broaden the adapter silently into a
general fast-glob replacement.
