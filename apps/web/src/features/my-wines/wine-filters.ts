import type { paths } from "@/lib/api/schema";

type ListQuery = NonNullable<paths["/api/v1/me/wines"]["get"]["parameters"]["query"]>;
export type WineFilters = Required<Pick<ListQuery, "q" | "sort" | "rating" | "vintage">>;

export const wineSorts = {
  LAST_CONSUMED: "Recently tried",
  NAME: "Name A–Z",
  RATING: "Highest rating",
} satisfies Record<WineFilters["sort"], string>;
export const ratingFilters = {
  ALL: "All ratings",
  RATED: "Rated",
  UNRATED: "Unrated",
} satisfies Record<WineFilters["rating"], string>;
export const vintageFilters = {
  ALL: "All vintages",
  YEAR: "Specific year",
  NON_VINTAGE: "Non-vintage",
  MULTI_VINTAGE: "Multi-vintage",
  UNKNOWN: "Vintage unknown",
} satisfies Record<WineFilters["vintage"], string>;

function option<T extends string>(
  value: string | null,
  choices: Record<T, string>,
  fallback: T,
): T {
  return value !== null && Object.hasOwn(choices, value) ? (value as T) : fallback;
}

export function readWineFilters(params: Pick<URLSearchParams, "get">): WineFilters {
  return {
    q: (params.get("q") ?? "").slice(0, 200).trim().replace(/\s+/g, " "),
    sort: option(params.get("sort"), wineSorts, "LAST_CONSUMED"),
    rating: option(params.get("rating"), ratingFilters, "ALL"),
    vintage: option(params.get("vintage"), vintageFilters, "ALL"),
  };
}

export function wineFilterQuery(filters: WineFilters): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.sort !== "LAST_CONSUMED") params.set("sort", filters.sort);
  if (filters.rating !== "ALL") params.set("rating", filters.rating);
  if (filters.vintage !== "ALL") params.set("vintage", filters.vintage);
  return params.size ? `?${params}` : "";
}
