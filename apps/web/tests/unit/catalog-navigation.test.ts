import assert from "node:assert/strict";
import { test } from "node:test";
import { browseHref, catalogSearch } from "../../src/features/catalog/navigation";

test("catalog navigation preserves literal search terms and the bounded page", () => {
  const q = "Ridge & château / 2022";
  const url = new URL(browseHref(q, 24), "https://example.test");
  assert.equal(url.pathname, "/browse");
  assert.deepEqual(catalogSearch(Object.fromEntries(url.searchParams)), { q, offset: 24 });
  assert.deepEqual(catalogSearch({ q: "  krug  " }), { q: "krug", offset: 0 });
  assert.equal(browseHref(""), "/browse");
});

test("catalog navigation rejects malformed and unbounded parameters", () => {
  for (const params of [
    { q: ["wine", "other"] },
    { q: "x".repeat(201) },
    { q: "\0" },
    { offset: "-1" },
    { offset: "10001" },
    { offset: "1e3" },
    { offset: ["1", "2"] },
  ])
    assert.equal(catalogSearch(params), null);
});
