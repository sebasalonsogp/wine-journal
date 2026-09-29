import { draftPrefix } from "@/lib/session/private-drafts";

export type RatingDraft = { score: number | null; version: number };

export function ratingKey(owner: string, wine: string) {
  return `${draftPrefix}rating:${owner}:${wine}`;
}

export function parseRatingDraft(raw: string | null): RatingDraft | null {
  try {
    if (!raw || raw.length > 200) return null;
    const value = JSON.parse(raw);
    if (!value || !Number.isSafeInteger(value.version) || value.version < 0) return null;
    if (
      value.score !== null &&
      (typeof value.score !== "number" ||
        value.score < 1 ||
        value.score > 5 ||
        !Number.isInteger(value.score * 2))
    )
      return null;
    return { score: value.score, version: value.version };
  } catch {
    return null;
  }
}

export function readRatingDraft(key: string): RatingDraft | null {
  try {
    return parseRatingDraft(sessionStorage.getItem(key));
  } catch {
    return null;
  }
}

export function storeRatingDraft(key: string, draft: RatingDraft | null): boolean {
  try {
    if (draft) sessionStorage.setItem(key, JSON.stringify(draft));
    else sessionStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}
