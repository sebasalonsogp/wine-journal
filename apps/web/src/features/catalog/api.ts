import "server-only";
import createClient from "openapi-fetch";
import type { paths } from "@/lib/api/schema";

export function publicApiOrigin() {
  const url = new URL(process.env.WINE_JOURNAL_API_URL ?? "");
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/" ||
    (url.protocol !== "https:" && !(local && url.protocol === "http:"))
  )
    throw new Error("Invalid API origin configuration.");
  return url.origin;
}

function publicApi() {
  // Guest reads never forward session cookies, authorization, or private API state.
  return createClient<paths>({
    baseUrl: publicApiOrigin(),
    cache: "no-store",
    credentials: "omit",
    redirect: "error",
    signal: AbortSignal.timeout(5000),
  });
}

export async function browseCatalog(q: string, offset: number) {
  try {
    const { data } = await publicApi().GET("/api/v1/catalog/wines", {
      params: { query: { q, offset, limit: 24 } },
    });
    return data ?? null;
  } catch {
    return null;
  }
}

export async function catalogDetails(id: string) {
  try {
    const { data, response } = await publicApi().GET("/api/v1/catalog/wines/{release_id}", {
      params: { path: { release_id: id } },
    });
    if (response.status === 404 || response.status === 422) return { kind: "missing" } as const;
    return data ? ({ kind: "found", wine: data } as const) : ({ kind: "unavailable" } as const);
  } catch {
    return { kind: "unavailable" } as const;
  }
}
