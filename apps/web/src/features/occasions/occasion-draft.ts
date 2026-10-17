import type { components } from "@/lib/api/schema";
import { draftPrefix } from "@/lib/session/private-drafts";

export type Occasion = components["schemas"]["OccasionResponse"];
export type OccasionDraft = {
  title: string;
  occasionDate: string;
  localTime: string;
  timezone: string;
  locationLabel: string;
  notes: string;
  version: number | null;
  intentKey: string;
  attempted: boolean;
};

export function occasionKey(owner: string, id?: string) {
  return `${draftPrefix}occasion:${owner}:${id ?? "new"}`;
}

export function newOccasionDraft(occasion?: Occasion): OccasionDraft {
  const today = new Date();
  return {
    title: occasion?.title ?? "",
    occasionDate:
      occasion?.occasionDate ??
      `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`,
    localTime: occasion?.localTime?.slice(0, 5) ?? "",
    timezone: occasion?.timezone ?? "",
    locationLabel: occasion?.locationLabel ?? "",
    notes: occasion?.notes ?? "",
    version: occasion?.version ?? null,
    intentKey: crypto.randomUUID(),
    attempted: false,
  };
}

export function parseOccasionDraft(raw: string | null): OccasionDraft | null {
  try {
    if (!raw || raw.length > 70000) return null;
    const value = JSON.parse(raw);
    if (
      !value ||
      typeof value.attempted !== "boolean" ||
      typeof value.intentKey !== "string" ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value.intentKey)
    )
      return null;
    if (value.version !== null && (!Number.isSafeInteger(value.version) || value.version < 1))
      return null;
    for (const [field, limit] of Object.entries({
      title: 200,
      occasionDate: 10,
      localTime: 5,
      timezone: 100,
      locationLabel: 200,
      notes: 10000,
    })) {
      if (typeof value[field] !== "string" || value[field].length > limit) return null;
    }
    return {
      title: value.title,
      occasionDate: value.occasionDate,
      localTime: value.localTime,
      timezone: value.timezone,
      locationLabel: value.locationLabel,
      notes: value.notes,
      version: value.version,
      intentKey: value.intentKey,
      attempted: value.attempted,
    };
  } catch {
    return null;
  }
}

export function readOccasionDraft(key: string): OccasionDraft | null {
  try {
    return parseOccasionDraft(sessionStorage.getItem(key));
  } catch {
    return null;
  }
}

export function storeOccasionDraft(key: string, draft: OccasionDraft | null): boolean {
  try {
    if (draft) sessionStorage.setItem(key, JSON.stringify(draft));
    else sessionStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function occasionBody(draft: OccasionDraft): components["schemas"]["OccasionFields"] {
  return {
    title: draft.title.trim() || null,
    occasionDate: draft.occasionDate,
    localTime: draft.localTime || null,
    timezone: draft.localTime ? draft.timezone.trim() : null,
    locationLabel: draft.locationLabel.trim() || null,
    notes: draft.notes || null,
  };
}
