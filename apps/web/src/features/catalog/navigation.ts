export function catalogSearch(params: Record<string, string | string[] | undefined>) {
  const q = params.q ?? "";
  const offset = params.offset ?? "0";
  if (
    typeof q !== "string" ||
    q.length > 200 ||
    /[\u0000-\u001f\u007f]/u.test(q) ||
    typeof offset !== "string" ||
    !/^\d{1,5}$/.test(offset) ||
    Number(offset) > 10000
  )
    return null;
  return { q: q.trim(), offset: Number(offset) };
}

export function browseHref(q: string, offset = 0) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (offset) params.set("offset", String(offset));
  return `/browse${params.size ? `?${params}` : ""}`;
}
