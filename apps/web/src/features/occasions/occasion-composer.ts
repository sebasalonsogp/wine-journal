import { entryBody, newDraft, parseDraft, type Fields } from "@/features/capture/draft";
import {
  newOccasionDraft,
  occasionBody,
  parseOccasionDraft,
  type OccasionDraft,
} from "./occasion-draft";
import type { components } from "@/lib/api/schema";

export type WineDraft = { fields: Fields; extraEntries: { consumedDate: string; notes: string }[] };
export type Composer = OccasionDraft & {
  wines: WineDraft[];
  child: WineDraft | null;
  editing: number | null;
};
export const entryCount = (wines: WineDraft[]) =>
  wines.reduce((count, wine) => count + 1 + wine.extraEntries.length, 0);
export function newComposer(base: OccasionDraft = newOccasionDraft()): Composer {
  return { ...base, wines: [], child: null, editing: null };
}
export function newWineDraft(day: string): WineDraft {
  return { fields: { ...newDraft(null).fields, consumedDate: day }, extraEntries: [] };
}
function parseWine(value: WineDraft): WineDraft | null {
  if (!value || !Array.isArray(value.extraEntries) || value.extraEntries.length > 19) return null;
  const parsed = parseDraft(
    JSON.stringify({ version: 1, ownerId: null, intentKey: null, fields: value.fields }),
  );
  if (!parsed || parsed.fields.newOccasion || parsed.fields.occasionId) return null;
  const extraEntries = [];
  for (const entry of value.extraEntries) {
    if (
      !entry ||
      typeof entry.consumedDate !== "string" ||
      entry.consumedDate.length > 10 ||
      typeof entry.notes !== "string" ||
      entry.notes.length > 10000
    )
      return null;
    extraEntries.push({ consumedDate: entry.consumedDate, notes: entry.notes });
  }
  return { fields: parsed.fields, extraEntries };
}
export function parseComposer(raw: string | null): Composer | null {
  try {
    if (!raw || raw.length > 1500000) return null;
    const value = JSON.parse(raw);
    const base = parseOccasionDraft(
      JSON.stringify({ ...value, wines: undefined, child: undefined, editing: undefined }),
    );
    if (!base) return null;
    if (value.wines === undefined) return newComposer(base);
    if (!Array.isArray(value.wines) || value.wines.length > 20) return null;
    const wines = value.wines.map(parseWine);
    if (wines.some((wine: WineDraft | null) => !wine)) return null;
    const editing = value.editing ?? null;
    if (editing !== null && (!Number.isInteger(editing) || editing < 0 || editing >= wines.length))
      return null;
    const child = value.child == null ? null : parseWine(value.child);
    if ((value.child != null && !child) || (!child && editing !== null)) return null;
    const pending = wines.filter((_: WineDraft, index: number) => index !== editing);
    if (entryCount(wines) > 20 || entryCount([...pending, ...(child ? [child] : [])]) > 20)
      return null;
    return { ...base, wines, child, editing };
  } catch {
    return null;
  }
}
export function readComposer(key: string): Composer | null {
  try {
    return parseComposer(sessionStorage.getItem(key));
  } catch {
    return null;
  }
}
export function wineBodies(wines: WineDraft[]): components["schemas"]["StagedWine"][] {
  return wines.map(({ fields, extraEntries }) => {
    const body = entryBody(fields);
    return {
      ...(body.releaseId ? { releaseId: body.releaseId } : { manualWine: body.manualWine }),
      entries: [
        { consumedDate: fields.consumedDate, notes: fields.notes || null },
        ...extraEntries.map((entry) => ({ ...entry, notes: entry.notes || null })),
      ],
    };
  });
}
export function composerBody(draft: Composer): components["schemas"]["CreateOccasion"] {
  return {
    ...occasionBody(draft),
    ...(draft.wines.length ? { wines: wineBodies(draft.wines) } : {}),
  };
}
