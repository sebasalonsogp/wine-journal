"use client";

import { CoverEditor } from "@/features/media/cover-editor";
import { BottleCover } from "@/features/media/bottle-cover";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { EntryEditor } from "@/features/capture/entry-editor";
import { EntryOccasion } from "@/features/occasions/entry-occasion";
import { EntryPhotos } from "@/features/media/photo-workspace";
import { WineRating } from "./wine-rating";
import { WineMoments } from "./wine-moments";
import { readWineFilters, wineFilterQuery } from "./wine-filters";
import { dateLabel, releaseLabel, JournalError } from "./wine-display";
import { RequestFailure } from "@/lib/session/http";

export function WineDetail({ wineId }: { wineId: string }) {
  const api = useJournalApi();
  const account = useAccount();
  const queries = useQueryClient();
  const params = useSearchParams();
  const filters = readWineFilters(params);
  const requestedEntry = params.get("entry");
  const focusedEntry =
    requestedEntry &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(requestedEntry)
      ? requestedEntry
      : undefined;
  const wineQuery = useQuery({
    queryKey: ["wine", account?.id, wineId],
    queryFn: () =>
      api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}", { params: { path: { wine_id: wineId } }, signal }),
      ),
  });
  const history = useInfiniteQuery({
    queryKey: ["entries", account?.id, wineId, focusedEntry],
    initialPageParam: undefined as string | undefined,
    enabled: Boolean(wineQuery.data),
    queryFn: async ({ pageParam }) => {
      if (focusedEntry) {
        const entry = await api.call((client, signal) =>
          client.GET("/api/v1/entries/{entry_id}", {
            params: { path: { entry_id: focusedEntry } },
            signal,
          }),
        );
        if (entry.userWineId !== wineId)
          throw new RequestFailure(404, "This drinking entry is unavailable for this wine.");
        return { items: [entry], nextCursor: null };
      }
      return api.call((client, signal) =>
        client.GET("/api/v1/me/wines/{wine_id}/entries", {
          params: { path: { wine_id: wineId }, query: { cursor: pageParam, limit: 20 } },
          signal,
        }),
      );
    },
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
              <BottleCover api={api} assetId={wine.coverAssetId} name={wine.name} />
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
            <details className="entry-photo-disclosure">
              <summary>Manage bottle cover</summary>
              <CoverEditor
                key={wine.id}
                api={api}
                wineId={wine.id}
                onSaved={() => {
                  void wineQuery.refetch();
                  void queries.invalidateQueries({ queryKey: ["wine-moments", account?.id] });
                }}
              />
            </details>
            <WineRating key={wine.id} wine={wine} />
            {!focusedEntry && <WineMoments wineId={wineId} />}
            <section className="wine-history" aria-labelledby="history-title">
              <div className="history-heading">
                <h2 id="history-title" tabIndex={-1}>
                  {focusedEntry ? "This photo’s drinking entry" : "Your drinking history"}
                </h2>
                <span>
                  {focusedEntry ? 1 : wine.entryCount}{" "}
                  {focusedEntry || wine.entryCount === 1 ? "entry" : "entries"}
                </span>
              </div>
              {focusedEntry && (
                <Link href={`/my-wines/${wineId}${wineFilterQuery(filters)}`} prefetch={false}>
                  Show all drinking history
                </Link>
              )}
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
                      <EntryOccasion entry={entry} />
                      <EntryPhotos api={api} entryId={entry.id} />
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
