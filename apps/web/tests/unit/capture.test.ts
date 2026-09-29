import assert from "node:assert/strict";
import { test } from "node:test";
import { entryBody, newDraft, parseDraft } from "../../src/features/capture/draft";
import { returnPath } from "../../src/features/auth/validation";

test("draft parsing rejects malformed state and retains only product fields", () => {
  const draft = newDraft("d8d1b63c-ce4d-4e61-83c0-8fa2d52c5440");
  draft.fields.name = "A private wine";
  draft.intentKey = crypto.randomUUID();
  assert.deepEqual(parseDraft(JSON.stringify({ ...draft, injected: "ignored" })), draft);
  for (const raw of [
    "null",
    "{}",
    "bad",
    JSON.stringify({ ...draft, ownerId: "invalid" }),
    JSON.stringify({ ...draft, fields: { ...draft.fields, name: 3 } }),
  ]) {
    assert.equal(parseDraft(raw), null);
  }
});

test("manual and existing-release saves have distinct minimal payloads", () => {
  const { fields } = newDraft(null);
  fields.name = "  Cabernet  ";
  fields.year = "2021";
  assert.equal(entryBody(fields).manualWine?.name, "Cabernet");
  assert.equal(entryBody(fields).manualWine?.year, null);
  fields.vintageStatus = "YEAR";
  assert.equal(entryBody(fields).manualWine?.year, 2021);
  fields.releaseId = crypto.randomUUID();
  assert.deepEqual(entryBody(fields), {
    consumedDate: fields.consumedDate,
    releaseId: fields.releaseId,
  });
});

test("sign-in can return only to capture or a valid private wine path", () => {
  assert.equal(returnPath("/capture"), "/capture");
  const path = `/my-wines/${crypto.randomUUID()}`;
  assert.equal(returnPath(path), path);
  for (const input of [
    path + "?next=https://evil.test",
    "/capture?wine=bad",
    path + "/../auth",
    "/my-wines/not-a-uuid",
  ])
    assert.equal(returnPath(input), "/my-wines");
});
