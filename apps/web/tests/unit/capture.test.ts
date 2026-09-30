import assert from "node:assert/strict";
import { test } from "node:test";
import { entryBody, newDraft, parseDraft } from "../../src/features/capture/draft";
import { returnPath } from "../../src/features/auth/validation";
import { newOccasionDraft } from "../../src/features/occasions/occasion-draft";

test("capture retains nested occasion and wine notes while preserving legacy retry payloads", () => {
  const draft = newDraft(null);
  draft.fields.name = "Cabernet";
  draft.fields.notes = "Wine note";
  draft.fields.newOccasion = newOccasionDraft();
  draft.fields.newOccasion.title = "Dinner";
  draft.fields.newOccasion.notes = "Occasion note";
  draft.intentKey = crypto.randomUUID();
  const restored = parseDraft(JSON.stringify(draft))!;
  assert.deepEqual(restored, draft);
  assert.equal(entryBody(restored.fields).newOccasion?.notes, "Occasion note");
  assert.equal(entryBody(restored.fields).notes, "Wine note");
  assert.equal(
    parseDraft(
      JSON.stringify({ ...draft, fields: { ...draft.fields, occasionId: crypto.randomUUID() } }),
    ),
    null,
  );
  assert.equal(
    parseDraft(JSON.stringify({ ...draft, fields: { ...draft.fields, notes: "x".repeat(10001) } })),
    null,
  );
  const legacy = JSON.parse(JSON.stringify(draft));
  delete legacy.fields.newOccasion;
  delete legacy.fields.occasionId;
  delete legacy.fields.notes;
  const upgraded = parseDraft(JSON.stringify(legacy))!;
  assert.equal(upgraded.intentKey, draft.intentKey);
  assert.equal(upgraded.fields.newOccasion, null);
  assert.equal(upgraded.fields.notes, "");
  assert.equal("newOccasion" in entryBody(upgraded.fields), false);
  assert.equal("notes" in entryBody(upgraded.fields), false);
});

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
