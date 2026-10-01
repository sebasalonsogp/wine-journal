import assert from "node:assert/strict";
import { test } from "node:test";
import {
  newOccasionDraft,
  occasionBody,
  occasionKey,
  parseOccasionDraft,
} from "../../src/features/occasions/occasion-draft";
import { returnPath } from "../../src/features/auth/validation";

test("occasion drafts keep creation keys, original versions and civil date/time", () => {
  const draft = newOccasionDraft();
  const pending = {
    ...draft,
    attempted: true,
    title: " Dinner ",
    occasionDate: "2026-01-01",
    localTime: "00:15",
    timezone: "Pacific/Kiritimati",
    notes: "First line\nSecond line",
  };
  assert.deepEqual(parseOccasionDraft(JSON.stringify({ ...pending, extra: "ignored" })), pending);
  assert.equal(occasionBody(pending).title, "Dinner");
  assert.equal(occasionBody(pending).occasionDate, "2026-01-01");
  assert.equal(occasionBody(pending).localTime, "00:15");
  assert.equal(occasionBody({ ...pending, title: " ", localTime: "" }).title, null);
  assert.equal(occasionBody({ ...pending, localTime: "" }).timezone, null);
  assert.notEqual(occasionKey("a", "occasion"), occasionKey("b", "occasion"));
});

test("occasion draft parsing rejects malformed or oversized state", () => {
  const draft = newOccasionDraft();
  for (const raw of [
    null,
    "bad",
    "{}",
    "null",
    JSON.stringify({ ...draft, version: 0 }),
    JSON.stringify({ ...draft, intentKey: "bad" }),
    JSON.stringify({ ...draft, notes: "x".repeat(10001) }),
    JSON.stringify({ ...draft, attempted: "true" }),
  ])
    assert.equal(parseOccasionDraft(raw), null);
});

test("occasion sign-in return paths remain explicit and local", () => {
  const id = "00000000-0000-4000-8000-000000000001";
  assert.equal(returnPath("/occasions/new"), "/occasions/new");
  assert.equal(returnPath(`/occasions/${id}`), `/occasions/${id}`);
  for (const value of [
    "//example.com/occasions/new",
    "/occasions/other",
    "/occasions/new?next=https://example.com",
  ])
    assert.equal(returnPath(value), "/my-wines");
});
