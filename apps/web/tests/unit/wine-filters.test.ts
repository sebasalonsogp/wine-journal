import assert from "node:assert/strict";
import { test } from "node:test";
import { readWineFilters, wineFilterQuery } from "../../src/features/my-wines/wine-filters";

test("wine filter URLs round-trip only supported choices and safely encode search", () => {
  const filters = readWineFilters(
    new URLSearchParams("q=+Reserve+++2021+&sort=RATING&rating=RATED&vintage=YEAR&token=private"),
  );
  assert.equal(filters.q, "Reserve 2021");
  assert.deepEqual(readWineFilters(new URLSearchParams(wineFilterQuery(filters))), filters);
  assert.ok(!wineFilterQuery(filters).includes("token"));
  assert.equal(wineFilterQuery(readWineFilters(new URLSearchParams())), "");
  const unusual = readWineFilters(new URLSearchParams({ q: "A&B #1 / 100%" }));
  assert.deepEqual(readWineFilters(new URLSearchParams(wineFilterQuery(unusual))), unusual);
});

test("unknown filter choices and excessive URL text have bounded defaults", () => {
  const filters = readWineFilters(
    new URLSearchParams({
      sort: "constructor",
      rating: "bad",
      vintage: "__proto__",
      q: "x".repeat(201),
    }),
  );
  assert.equal(filters.sort, "LAST_CONSUMED");
  assert.equal(filters.rating, "ALL");
  assert.equal(filters.vintage, "ALL");
  assert.equal(filters.q.length, 200);
});
