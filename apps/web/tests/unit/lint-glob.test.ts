import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { ESLint } from "eslint";

const require = createRequire(import.meta.url);
const pluginEntry = require.resolve("@next/eslint-plugin-next");
const { getRootDirs } = require(path.join(path.dirname(pluginEntry), "utils/get-root-dirs.js")) as {
  getRootDirs(context: {
    cwd: string;
    settings: { next?: { rootDir: string | string[] } };
  }): string[];
};
const slash = (value: string) => value.replaceAll("\\", "/");

test("Next lint glob override preserves relative directory patterns", () => {
  const root = mkdtempSync(path.join(process.cwd(), ".lint-root-"));
  try {
    mkdirSync(path.join(root, "app"));
    writeFileSync(path.join(root, "not-a-directory.txt"), "fixture");
    const relative = slash(path.relative(process.cwd(), root));
    assert.deepEqual(
      getRootDirs({ cwd: process.cwd(), settings: { next: { rootDir: `${relative}/*` } } }),
      [`${relative}/app`],
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("Next lint glob override preserves root discovery and route linting", async () => {
  const root = mkdtempSync(path.join(tmpdir(), "wine-lint-"));
  try {
    const first = path.join(root, "apps/first");
    const second = path.join(root, "apps/second");
    mkdirSync(path.join(first, "pages"), { recursive: true });
    mkdirSync(second, { recursive: true });
    writeFileSync(path.join(first, "pages/about.tsx"), "export default function About() {}");
    writeFileSync(path.join(root, "apps/not-a-directory.txt"), "fixture");

    assert.deepEqual(getRootDirs({ cwd: first, settings: {} }), [first]);
    for (const rootDir of [
      slash(path.join(root, "apps/*")),
      [slash(first), slash(second)],
      slash(path.join(root, "apps/{first,second}")),
    ]) {
      assert.deepEqual(
        getRootDirs({ cwd: root, settings: { next: { rootDir } } })
          .map(slash)
          .sort(),
        [first, second].map(slash).sort(),
      );
    }
    assert.deepEqual(
      getRootDirs({ cwd: root, settings: { next: { rootDir: first.replaceAll("/", "\\") } } }).map(
        slash,
      ),
      [slash(first)],
    );

    const eslint = new ESLint({
      overrideConfig: { settings: { next: { rootDir: slash(path.join(root, "apps/*")) } } },
    });
    const [result] = await eslint.lintText(
      'export default function Probe() { return <a href="/about">About</a>; }',
      { filePath: "src/lint-probe.tsx" },
    );
    assert.ok(
      result.messages.some((message) => message.ruleId === "@next/next/no-html-link-for-pages"),
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
