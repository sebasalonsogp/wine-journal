import type { components } from "@/lib/api/schema";
import { draftPrefix } from "@/lib/session/private-drafts";

export type SaveEntry = components["schemas"]["SaveEntry"];
export type Fields = {
  name: string;
  producer: string;
  vintageStatus: "YEAR" | "NON_VINTAGE" | "MULTI_VINTAGE" | "UNKNOWN";
  year: string;
  edition: string;
  consumedDate: string;
  releaseId: string | null;
};
export type Draft = {
  version: 1;
  ownerId: string | null;
  fields: Fields;
  intentKey: string | null;
};
const key = draftPrefix + "capture";
export const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function newDraft(ownerId: string | null): Draft {
  const today = new Date();
  const consumedDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return {
    version: 1,
    ownerId,
    intentKey: null,
    fields: {
      name: "",
      producer: "",
      vintageStatus: "UNKNOWN",
      year: "",
      edition: "",
      consumedDate,
      releaseId: null,
    },
  };
}

export function parseDraft(raw: string | null): Draft | null {
  if (!raw || raw.length > 5000) return null;
  try {
    const value = JSON.parse(raw);
    const fields = value.fields;
    if (
      value.version !== 1 ||
      !fields ||
      (value.ownerId !== null &&
        (typeof value.ownerId !== "string" || !uuid.test(value.ownerId))) ||
      (value.intentKey !== null &&
        (typeof value.intentKey !== "string" || !uuid.test(value.intentKey))) ||
      (fields.releaseId !== null &&
        (typeof fields.releaseId !== "string" || !uuid.test(fields.releaseId))) ||
      !["YEAR", "NON_VINTAGE", "MULTI_VINTAGE", "UNKNOWN"].includes(fields.vintageStatus) ||
      !["name", "producer", "year", "edition", "consumedDate"].every(
        (name) => typeof fields[name] === "string" && fields[name].length <= 200,
      )
    )
      return null;
    // Only product fields survive parsing; never spread arbitrary stored data into API input.
    return {
      version: 1,
      ownerId: value.ownerId,
      intentKey: value.intentKey,
      fields: {
        name: fields.name,
        producer: fields.producer,
        year: fields.year,
        edition: fields.edition,
        consumedDate: fields.consumedDate,
        vintageStatus: fields.vintageStatus,
        releaseId: fields.releaseId,
      },
    };
  } catch {
    return null;
  }
}

export function readDraft(): Draft | null {
  try {
    return parseDraft(sessionStorage.getItem(key));
  } catch {
    return null;
  }
}
export function writeDraft(draft: Draft): boolean {
  try {
    sessionStorage.setItem(key, JSON.stringify(draft));
    return true;
  } catch {
    return false;
  }
}
export function removeDraft() {
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* Storage may be unavailable. */
  }
}

export function entryBody(fields: Fields): SaveEntry {
  if (fields.releaseId) return { consumedDate: fields.consumedDate, releaseId: fields.releaseId };
  return {
    consumedDate: fields.consumedDate,
    manualWine: {
      name: fields.name.trim(),
      producer: fields.producer.trim() || null,
      vintageStatus: fields.vintageStatus,
      year: fields.vintageStatus === "YEAR" ? Number(fields.year) : null,
      edition: fields.edition.trim() || null,
    },
  };
}
