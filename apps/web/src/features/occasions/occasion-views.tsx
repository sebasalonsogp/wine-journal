"use client";

import Link from "next/link";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { dateLabel, JournalError } from "@/features/my-wines/wine-display";
import { OccasionEditor } from "./occasion-editor";

export function OccasionList() {
  const api = useJournalApi();
  const account = useAccount()!;
  const query = useInfiniteQuery({
    queryKey: ["occasions", account.id],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.call((client, signal) =>
        client.GET("/api/v1/occasions", {
          params: { query: { cursor: pageParam, limit: 20 } },
          signal,
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const occasions = query.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <main id="main" className="page-content">
      <div className="journal-page-head">
        <div>
          <h1>Occasions</h1>
          <p className="page-intro">The people, places, and moments worth remembering.</p>
        </div>
        <Link className="button" href="/occasions/new" prefetch={false}>
          New occasion
        </Link>
      </div>
      {query.isPending ? (
        <p className="journal-loading" role="status">
          Opening your occasions…
        </p>
      ) : query.error ? (
        <JournalError error={query.error} retry={() => void query.refetch()} />
      ) : occasions.length === 0 ? (
        <section className="empty-state">
          <h2>A place for the moments.</h2>
          <p>A dinner with friends, a winery visit, or a quiet evening worth keeping.</p>
          <Link className="button button-secondary" href="/occasions/new" prefetch={false}>
            Create your first occasion
          </Link>
        </section>
      ) : (
        <>
          <p className="list-order">By occasion date · newest first</p>
          <ul className="occasion-list">
            {occasions.map((occasion) => (
              <li key={occasion.id}>
                <Link className="occasion-card" href={`/occasions/${occasion.id}`} prefetch={false}>
                  <time dateTime={occasion.occasionDate}>{dateLabel(occasion.occasionDate)}</time>
                  <div>
                    <h2>{occasion.title || dateLabel(occasion.occasionDate)}</h2>
                    {occasion.locationLabel && (
                      <p className="occasion-place">{occasion.locationLabel}</p>
                    )}
                    {occasion.notes && <p className="occasion-note-preview">{occasion.notes}</p>}
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
              {query.isFetchingNextPage ? "Loading…" : "Load more occasions"}
            </button>
          )}
        </>
      )}
      <footer className="journal-footer">
        Your occasions are private.<span>Everyday glasses can stay in My wines.</span>
      </footer>
    </main>
  );
}

export function NewOccasion() {
  return (
    <main id="main" className="page-content occasion-page">
      <Link className="back-link" href="/occasions">
        Back to Occasions
      </Link>
      <h1>New occasion</h1>
      <p className="page-intro">Start with a date. Add the details you want to remember.</p>
      <OccasionEditor />
    </main>
  );
}

export function OccasionDetail({ occasionId }: { occasionId: string }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const query = useQuery({
    queryKey: ["occasion", account.id, occasionId],
    queryFn: () =>
      api.call((client, signal) =>
        client.GET("/api/v1/occasions/{occasion_id}", {
          params: { path: { occasion_id: occasionId } },
          signal,
        }),
      ),
  });
  const occasion = query.data;
  return (
    <main id="main" className="page-content occasion-page">
      <Link className="back-link" href="/occasions">
        Back to Occasions
      </Link>
      {query.isPending ? (
        <p role="status">Opening this occasion…</p>
      ) : query.error ? (
        <JournalError error={query.error} retry={() => void query.refetch()} />
      ) : (
        occasion && (
          <>
            <header className="occasion-heading">
              <h1>{occasion.title || dateLabel(occasion.occasionDate)}</h1>
              <p>
                <time dateTime={occasion.occasionDate}>{dateLabel(occasion.occasionDate)}</time>
                {occasion.localTime &&
                  ` · ${occasion.localTime.slice(0, 5)} · ${occasion.timezone}`}
              </p>
              {occasion.locationLabel && <p className="occasion-place">{occasion.locationLabel}</p>}
            </header>
            <section className="occasion-notes" aria-label="Saved occasion notes">
              {occasion.notes ? (
                <p className="entry-notes">{occasion.notes}</p>
              ) : (
                <p>No notes yet. Come back whenever a detail comes to mind.</p>
              )}
            </section>
            <OccasionEditor key={occasion.id} occasion={occasion} />
            <p className="occasion-availability">
              You can link an occasion when logging a wine. Wine lists and photo memories here are
              coming soon.
            </p>
          </>
        )
      )}
    </main>
  );
}
