import assert from "node:assert/strict";
import { test } from "node:test";
import { parseRatingDraft, ratingKey } from "../../src/features/my-wines/rating-draft";

test("rating drafts retain the original version and are scoped by account and wine", () => {
  assert.deepEqual(parseRatingDraft('{"score":4.5,"version":3,"extra":"ignored"}'), {
    score: 4.5,
    version: 3,
  });
  assert.deepEqual(parseRatingDraft('{"score":null,"version":0}'), { score: null, version: 0 });
  assert.notEqual(ratingKey("a", "wine"), ratingKey("b", "wine"));
  assert.notEqual(ratingKey("a", "wine"), ratingKey("a", "other"));
});

test("rating drafts reject malformed, oversized and off-scale values", () => {
  for (const raw of [
    null,
    "null",
    "{}",
    "bad",
    "x".repeat(201),
    ...[true, 0, 5.5, 4.2, "4"].map((score) => JSON.stringify({ score, version: 0 })),
    '{"score":4,"version":-1}',
    '{"score":4,"version":0.5}',
  ])
    assert.equal(parseRatingDraft(raw), null);
});
