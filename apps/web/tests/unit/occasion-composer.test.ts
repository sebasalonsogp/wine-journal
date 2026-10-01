import assert from "node:assert/strict";
import { test } from "node:test";
import {
  newComposer,
  newWineDraft,
  parseComposer,
  composerBody,
  entryCount,
} from "../../src/features/occasions/occasion-composer";
import { newOccasionDraft, occasionBody } from "../../src/features/occasions/occasion-draft";

test("occasion composer preserves pending children, repetitions and legacy retry bodies", () => {
  const legacy = newOccasionDraft();
  legacy.attempted = true;
  assert.deepEqual(composerBody(parseComposer(JSON.stringify(legacy))!), occasionBody(legacy));
  const draft = newComposer();
  const wine = newWineDraft("2026-09-29");
  wine.fields.name = "Red";
  wine.extraEntries.push({ consumedDate: "2026-09-28", notes: "Earlier glass" });
  draft.wines = [wine];
  draft.child = newWineDraft("2026-09-30");
  draft.child.fields.name = "Unfinished white";
  const restored = parseComposer(JSON.stringify(draft))!;
  assert.deepEqual(restored, draft);
  assert.equal(entryCount(restored.wines), 2);
  const body = composerBody(restored);
  assert.equal(body.wines?.length, 1);
  assert.equal(body.wines?.[0].entries[1].notes, "Earlier glass");
  assert.equal(JSON.stringify(body).includes("Unfinished white"), false);
});

test("occasion composer rejects invalid, nested or excessive batches", () => {
  const draft = newComposer();
  const wine = newWineDraft("2026-09-29");
  for (const value of [
    { ...draft, wines: Array(21).fill(wine) },
    { ...draft, wines: [wine], editing: 2, child: wine },
    { ...draft, wines: [{ ...wine, fields: { ...wine.fields, newOccasion: newOccasionDraft() } }] },
    { ...draft, wines: [{ ...wine, extraEntries: [{ consumedDate: "2026-09-29", notes: 123 }] }] },
    { ...draft, wines: Array(20).fill(wine), child: wine },
  ])
    assert.equal(parseComposer(JSON.stringify(value)), null);
});
