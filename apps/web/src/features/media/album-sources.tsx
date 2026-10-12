"use client";

import Link from "next/link";
import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { JournalError } from "@/features/my-wines/wine-display";

export function AlbumSources({
  occasionId,
  assetId,
  count,
}: {
  occasionId: string;
  assetId: string;
  count: number;
}) {
  const [opened, setOpened] = useState(false);
  const api = useJournalApi();
  const account = useAccount()!;
  const query = useInfiniteQuery({
    queryKey: ["album-sources", account.id, occasionId, assetId],
    enabled: opened,
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      api.call((client, timeout) =>
        client.GET("/api/v1/occasions/{occasion_id}/album/{asset_id}/sources", {
          params: {
            path: { occasion_id: occasionId, asset_id: assetId },
            query: { limit: 20, offset: pageParam },
          },
          signal: AbortSignal.any([signal, timeout]),
        }),
      ),
    getNextPageParam: (page) => page.nextOffset ?? undefined,
  });
  const sources = [
    ...new Map(
      query.data?.pages
        .flatMap((page) => page.items)
        .map((source) => [`${source.kind}:${source.parentId}`, source]),
    ).values(),
  ];
  return (
    <details className="album-sources" onToggle={(event) => setOpened(event.currentTarget.open)}>
      <summary>{count === 1 ? "Photo source" : `Photo sources (${count})`}</summary>
      {opened && (
        <>
          {query.isPending && <p role="status">Opening photo sources…</p>}
          {query.error && <JournalError error={query.error} retry={() => void query.refetch()} />}
          <ul>
            {sources.map((source) => (
              <li key={`${source.kind}:${source.parentId}`}>
                {source.kind === "OCCASION" ? (
                  <p>Added to this occasion</p>
                ) : (
                  <Link
                    href={`/my-wines/${source.userWineId}?entry=${source.parentId}#history-title`}
                    prefetch={false}
                  >
                    Open wine & drinking history
                  </Link>
                )}
                {source.caption && <p className="album-caption">{source.caption}</p>}
                {source.kind === "ENTRY" && (
                  <p className="form-footnote">Edit this photo in its wine entry.</p>
                )}
              </li>
            ))}
          </ul>
          {query.hasNextPage && (
            <button
              type="button"
              className="text-button"
              disabled={query.isFetching}
              onClick={() => void query.fetchNextPage()}
            >
              Load more sources
            </button>
          )}
        </>
      )}
    </details>
  );
}
