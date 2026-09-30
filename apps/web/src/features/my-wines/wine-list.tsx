"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { BottlePlaceholder, dateLabel, releaseLabel, JournalError } from "./wine-display";
import { WineFilterBar } from "./wine-filter-bar";
import { readWineFilters, wineFilterQuery, wineSorts, type WineFilters } from "./wine-filters";

export function WineList() {
  const api = useJournalApi();
  const account = useAccount();
  const searchParams = useSearchParams();
  const filters = readWineFilters(searchParams);
  const filterQuery = wineFilterQuery(filters);
  const filtered = Boolean(filters.q || filters.rating !== "ALL" || filters.vintage !== "ALL");
  function apply(next: WineFilters) {
    const target = wineFilterQuery(next);
    if (target !== filterQuery) window.history.pushState(null, "", `/my-wines${target}`);
  }
  function clearFilters() {
    apply({ ...filters, q: "", rating: "ALL", vintage: "ALL" });
  }
  const query = useInfiniteQuery({
    queryKey: ["wines", account?.id, filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines", {
          params: { query: { ...filters, cursor: pageParam, limit: 20 } },
          signal,
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const wines = query.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <main id="main" className="page-content">
      <div className="journal-page-head">
        <div>
          <h1>My wines</h1>
          <p className="page-intro">Wines you’ve tried. Moments worth keeping.</p>
        </div>
        <Link className="button" href="/capture" prefetch={false}>
          Log a wine
        </Link>
      </div>
      <WineFilterBar key={filterQuery} filters={filters} apply={apply} />
      {filtered && (
        <button className="text-button clear-wine-filters" type="button" onClick={clearFilters}>
          Clear filters
        </button>
      )}
      {query.isPending ? (
        <p className="journal-loading" role="status">
          Opening your wines…
        </p>
      ) : query.error ? (
        <JournalError error={query.error} retry={() => void query.refetch()} />
      ) : wines.length === 0 && filtered ? (
        <section className="empty-state" aria-live="polite">
          <h2>No wines match these filters.</h2>
          <p>
            Try part of a name, a producer or a year, or clear your filters to see all your wines.
          </p>
          <button className="button button-secondary" onClick={clearFilters}>
            Show all my wines
          </button>
        </section>
      ) : wines.length === 0 ? (
        <section className="empty-state">
          <h2>Your first page is waiting.</h2>
          <p>Start with a bottle or glass you’ve tried. A name and date are enough.</p>
          <Link className="button button-secondary" href="/capture">
            Add your first wine
          </Link>
        </section>
      ) : (
        <>
          <p className="list-order" role="status">
            {wineSorts[filters.sort]} · {wines.length} {wines.length === 1 ? "wine" : "wines"} shown
          </p>
          <ul className="wine-grid">
            {wines.map((wine) => (
              <li key={wine.id}>
                <Link
                  className="wine-card"
                  href={`/my-wines/${wine.id}${filterQuery}`}
                  prefetch={false}
                >
                  <BottlePlaceholder />
                  <div className="wine-card-content">
                    {wine.producer && <p className="wine-producer">{wine.producer}</p>}
                    <h2>{wine.name}</h2>
                    <p className="wine-release">{releaseLabel(wine)}</p>
                    <p className="wine-card-rating">
                      {wine.currentRating === null
                        ? "Not rated yet"
                        : `My rating: ${wine.currentRating} / 5`}
                    </p>
                    <div className="wine-card-history">
                      <p>
                        {wine.lastConsumedDate
                          ? `Last tried ${dateLabel(wine.lastConsumedDate)}`
                          : "No drinking entries yet"}
                      </p>
                      <p>
                        {wine.entryCount} {wine.entryCount === 1 ? "entry" : "entries"}
                      </p>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          {query.hasNextPage && (
            <button
              className="button button-secondary load-more"
              disabled={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              {query.isFetchingNextPage ? "Loading…" : "Load more wines"}
            </button>
          )}
        </>
      )}
      <footer className="journal-footer">
        Your journal is private.<span>Every vintage keeps its own story.</span>
      </footer>
    </main>
  );
}
