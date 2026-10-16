"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { PhotoFrame } from "@/features/media/photo-card";
import { dateLabel, JournalError } from "./wine-display";

export function WineMoments({ wineId }: { wineId: string }) {
  const api = useJournalApi();
  const account = useAccount()!;
  const params = useSearchParams();
  const queries = useQueryClient();
  const expanded = params.get("moments") === "all";
  const queryKey = ["wine-moments", account.id, wineId, expanded];
  const query = useInfiniteQuery({
    queryKey,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) =>
      api.call((client, timeout) =>
        client.GET("/api/v1/me/wines/{wine_id}/moments", {
          params: {
            path: { wine_id: wineId },
            query: { cursor: pageParam, limit: expanded ? 20 : 3 },
          },
          signal: AbortSignal.any([signal, timeout]),
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const photos = [
    ...new Map(
      query.data?.pages.flatMap((page) => page.items).map((photo) => [photo.assetId, photo]),
    ).values(),
  ];
  const galleryParams = new URLSearchParams(params);
  if (expanded) galleryParams.delete("moments");
  else galleryParams.set("moments", "all");
  const galleryQuery = galleryParams.toString();
  const reload = () => void queries.resetQueries({ queryKey, exact: true });

  if (!query.isPending && !query.error && photos.length === 0) return null;
  return (
    <section className="wine-moments" aria-labelledby="moments-title">
      <div className="photo-heading">
        <h2 id="moments-title" tabIndex={-1}>
          Moments with this wine
        </h2>
        <button type="button" className="text-button" onClick={reload} disabled={query.isFetching}>
          Reload memories
        </button>
      </div>
      <p className="form-footnote">
        Your entry photos and shared occasion memories, newest dates first.
      </p>
      {query.isPending && <p role="status">Opening your memories…</p>}
      {query.error && <JournalError error={query.error} retry={reload} />}
      {photos.length > 0 && (
        <>
          <ul className="photo-gallery">
            {photos.map((photo) => (
              <li className="photo-card" key={photo.assetId} data-testid="wine-moment">
                <PhotoFrame api={api} photo={{ ...photo, caption: photo.source.caption }} />
                {photo.source.caption && <p className="album-caption">{photo.source.caption}</p>}
                <time dateTime={photo.source.sourceDate}>{dateLabel(photo.source.sourceDate)}</time>
                <Link
                  className="album-entry-link"
                  href={
                    photo.source.kind === "ENTRY"
                      ? `/my-wines/${wineId}?entry=${photo.source.parentId}#history-title`
                      : `/occasions/${photo.source.parentId}`
                  }
                  prefetch={false}
                >
                  {photo.source.kind === "ENTRY" ? "Open drinking entry" : "Open occasion"}
                </Link>
              </li>
            ))}
          </ul>
          <Link
            className="album-entry-link"
            href={`/my-wines/${wineId}${galleryQuery ? `?${galleryQuery}` : ""}#moments-title`}
            prefetch={false}
          >
            {expanded ? "Show highlights" : "View all memories"}
          </Link>
        </>
      )}
      {expanded && query.hasNextPage && (
        <button
          type="button"
          className="button button-secondary load-more"
          disabled={query.isFetching}
          onClick={() => void query.fetchNextPage()}
        >
          {query.isFetchingNextPage ? "Loading…" : "Load more memories"}
        </button>
      )}
    </section>
  );
}
