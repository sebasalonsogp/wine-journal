"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { EntryEditor } from "@/features/capture/entry-editor";
import { WineRating } from "./wine-rating";
import { readWineFilters, wineFilterQuery } from "./wine-filters";
import { BottlePlaceholder, dateLabel, releaseLabel, JournalError } from "./wine-display";

export function WineDetail({ wineId }: { wineId: string }) {
  const api = useJournalApi();
  const account = useAccount();
  const filters = readWineFilters(useSearchParams());
  const wineQuery = useQuery({
    queryKey: ["wine", account?.id, wineId],
    queryFn: () =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}", { params: { path: { wine_id: wineId } }, signal }),
      ),
  });
  const history = useInfiniteQuery({
    queryKey: ["entries", account?.id, wineId],
    initialPageParam: undefined as string | undefined,
    enabled: Boolean(wineQuery.data),
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}/entries", {
          params: { path: { wine_id: wineId }, query: { cursor: pageParam, limit: 20 } },
          signal,
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const wine = wineQuery.data;
  const entries = history.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <main id="main" className="page-content">
      <Link className="back-link" href={`/my-wines${wineFilterQuery(filters)}`}>
        Back to My wines
      </Link>
      {wineQuery.isPending ? (
        <p className="journal-loading" role="status">
          Opening this wine…
        </p>
      ) : wineQuery.error ? (
        <JournalError error={wineQuery.error} retry={() => void wineQuery.refetch()} />
      ) : (
        wine && (
          <>
            <section className="wine-record">
              <BottlePlaceholder />
              <div>
                {wine.producer && <p className="wine-producer">{wine.producer}</p>}
                <h1>{wine.name}</h1>
                <p className="wine-release">{releaseLabel(wine)}</p>
                <p className="wine-private">Your private wine record</p>
                <Link className="button" href={`/capture?wine=${wine.id}`} prefetch={false}>
                  Log this wine again
                </Link>
              </div>
            </section>
            <WineRating key={wine.id} wine={wine} />
            <section className="wine-history" aria-labelledby="history-title">
              <div className="history-heading">
                <h2 id="history-title" tabIndex={-1}>
                  Your drinking history
                </h2>
                <span>
                  {wine.entryCount} {wine.entryCount === 1 ? "entry" : "entries"}
                </span>
              </div>
              {history.isPending ? (
                <p role="status">Opening your entries…</p>
              ) : history.error ? (
                <JournalError error={history.error} retry={() => void history.refetch()} />
              ) : entries.length === 0 ? (
                <p>No drinking entries yet.</p>
              ) : (
                <ol className="entry-history">
                  {entries.map((entry) => (
                    <li key={entry.id} data-testid="drinking-entry">
                      <time dateTime={entry.consumedDate}>{dateLabel(entry.consumedDate)}</time>
                      {entry.localTime && (
                        <p>
                          {entry.localTime.slice(0, 5)} · {entry.timezone}
                        </p>
                      )}
                      {entry.locationLabel && <p>{entry.locationLabel}</p>}
                      {entry.notes && <p className="entry-notes">{entry.notes}</p>}
                      {entry.occasionId && (
                        <p>
                          <Link href={`/occasions/${entry.occasionId}`} prefetch={false}>
                            View occasion
                          </Link>
                        </p>
                      )}
                      <EntryEditor
                        entry={entry}
                        label={`${wine.name} · ${dateLabel(entry.consumedDate)}`}
                      />
                    </li>
                  ))}
                </ol>
              )}
              {history.hasNextPage && (
                <button
                  className="button button-secondary load-more"
                  disabled={history.isFetchingNextPage}
                  onClick={() => void history.fetchNextPage()}
                >
                  {history.isFetchingNextPage ? "Loading…" : "Load more entries"}
                </button>
              )}
            </section>
          </>
        )
      )}
    </main>
  );
}
