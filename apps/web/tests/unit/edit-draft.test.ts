import assert from "node:assert/strict";
import { test } from "node:test";
import { editBody, entryDraft, parseEditDraft } from "../../src/features/capture/edit-draft";

const entry = {
  id: "entry",
  userWineId: "wine",
  consumedDate: "2026-01-01",
  createdAt: "2026-09-29T12:00:00Z",
  version: 3,
};

test("edit drafts preserve civil dates, unknown time and the original version", () => {
  const draft = entryDraft(entry);
  const body = editBody({ ...draft, notes: "A memory", locationLabel: " Home " });
  assert.equal(body.version, 3);
  assert.equal(body.consumedDate, "2026-01-01");
  assert.equal(body.localTime, null);
  assert.equal(body.timezone, null);
  assert.equal(body.locationLabel, "Home");
  assert.equal(editBody({ ...draft, notes: "", timezone: "UTC" }).notes, null);
});

test("stored edit drafts are bounded, ignore extra fields and reject malformed versions", () => {
  const draft = entryDraft(entry);
  assert.deepEqual(parseEditDraft(JSON.stringify({ ...draft, extra: "ignored" })), draft);
  for (const raw of [
    null,
    "null",
    "bad",
    "{}",
    JSON.stringify({ ...draft, version: 0 }),
    JSON.stringify({ ...draft, notes: "a".repeat(10001) }),
  ])
    assert.equal(parseEditDraft(raw), null);
  const escaped = { ...draft, notes: "\n".repeat(10000) };
  assert.deepEqual(parseEditDraft(JSON.stringify(escaped)), escaped);
});
