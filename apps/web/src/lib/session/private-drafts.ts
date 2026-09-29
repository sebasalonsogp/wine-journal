export const draftPrefix = "wine-journal:draft:";

export function clearPrivateDrafts() {
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index--) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(draftPrefix)) sessionStorage.removeItem(key);
    }
  } catch {
    // Storage may be disabled. In-memory state is cleared by the following navigation.
  }
}
