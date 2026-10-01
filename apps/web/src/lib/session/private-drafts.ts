export const draftPrefix = "wine-journal:draft:";
export const privateResetEvent = "wine-journal-private-reset";

export function clearPrivateDrafts() {
  // Session ending must clear in-memory work and bypass unsaved-work navigation guards.
  if (typeof window !== "undefined") window.dispatchEvent(new Event(privateResetEvent));
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index--) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(draftPrefix)) sessionStorage.removeItem(key);
    }
  } catch {
    // Storage may be disabled. In-memory state is cleared by the following navigation.
  }
}
