"use client";

import Link from "next/link";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { BottlePlaceholder, dateLabel, releaseLabel, JournalError } from "./wine-display";

export function WineList() {
  const api = useJournalApi();
  const account = useAccount();
  const query = useInfiniteQuery({
    queryKey: ["wines", account?.id],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines", {
          params: { query: { cursor: pageParam, limit: 20 } },
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
      {query.isPending ? (
        <p className="journal-loading" role="status">
          Opening your wines…
        </p>
      ) : query.error ? (
        <JournalError error={query.error} retry={() => void query.refetch()} />
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
          <p className="list-order">Recently tried</p>
          <ul className="wine-grid">
            {wines.map((wine) => (
              <li key={wine.id}>
                <Link className="wine-card" href={`/my-wines/${wine.id}`} prefetch={false}>
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
