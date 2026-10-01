import type { components } from "@/lib/api/schema";
import { draftPrefix } from "@/lib/session/private-drafts";

export type Entry = components["schemas"]["EntryResponse"];
export type EditDraft = {
  version: number;
  consumedDate: string;
  localTime: string;
  timezone: string;
  locationLabel: string;
  notes: string;
};

export function entryDraft(entry: Entry): EditDraft {
  return {
    version: entry.version ?? 1,
    consumedDate: entry.consumedDate,
    localTime: entry.localTime?.slice(0, 5) ?? "",
    timezone: entry.timezone ?? "",
    locationLabel: entry.locationLabel ?? "",
    notes: entry.notes ?? "",
  };
}

export function editKey(owner: string, entry: string) {
  return `${draftPrefix}edit:${owner}:${entry}`;
}

export function parseEditDraft(raw: string | null): EditDraft | null {
  try {
    if (!raw || raw.length > 70000) return null;
    const value = JSON.parse(raw);
    if (!value || !Number.isSafeInteger(value.version) || value.version < 1) return null;
    const lengths = {
      consumedDate: 10,
      localTime: 5,
      timezone: 100,
      locationLabel: 200,
      notes: 10000,
    };
    for (const [field, maximum] of Object.entries(lengths))
      if (typeof value[field] !== "string" || value[field].length > maximum) return null;
    return {
      version: value.version,
      consumedDate: value.consumedDate,
      localTime: value.localTime,
      timezone: value.timezone,
      locationLabel: value.locationLabel,
      notes: value.notes,
    };
  } catch {
    return null;
  }
}

export function readEditDraft(key: string): EditDraft | null {
  try {
    return parseEditDraft(sessionStorage.getItem(key));
  } catch {
    return null;
  }
}

export function storeEditDraft(key: string, draft: EditDraft | null): boolean {
  try {
    if (draft) sessionStorage.setItem(key, JSON.stringify(draft));
    else sessionStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function editBody(draft: EditDraft): components["schemas"]["EditEntry"] {
  return {
    ...draft,
    localTime: draft.localTime || null,
    timezone: draft.localTime ? draft.timezone : null,
    locationLabel: draft.locationLabel.trim() || null,
    notes: draft.notes || null,
  };
}
