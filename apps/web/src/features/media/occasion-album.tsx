"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState } from "react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useAccount, useJournalApi } from "@/features/auth/journal-shell";
import { JournalError } from "@/features/my-wines/wine-display";
import { privateResetEvent } from "@/lib/session/private-drafts";
import { PhotoCard, PhotoFrame } from "./photo-card";
import { PhotoSelection, type SelectedPhoto } from "./photo-selection";
import { PHOTO_ACCEPT, photoType } from "./photo-upload";
import { usePendingImages } from "./use-pending-images";
import { AlbumSources } from "./album-sources";

export function OccasionAlbum({ occasionId }: { occasionId: string }) {
  const id = useId();
  const api = useJournalApi();
  const account = useAccount()!;
  const queries = useQueryClient();
  const [selected, setSelected] = useState<SelectedPhoto[]>([]);
  const [selectionError, setSelectionError] = useState("");
  const [ended, setEnded] = useState(false);
  usePendingImages(selected.length > 0);
  useEffect(() => {
    const reset = () => {
      setEnded(true);
      setSelected([]);
    };
    window.addEventListener(privateResetEvent, reset);
    return () => window.removeEventListener(privateResetEvent, reset);
  }, []);
  const query = useInfiniteQuery({
    queryKey: ["occasion-album", account.id, occasionId],
    enabled: !ended,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) =>
      api.call((client, timeout) =>
        client.GET("/api/v1/occasions/{occasion_id}/album", {
          params: { path: { occasion_id: occasionId }, query: { cursor: pageParam, limit: 20 } },
          signal: AbortSignal.any([signal, timeout]),
        }),
      ),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
    refetchInterval: (current) =>
      !current.state.error &&
      current.state.dataUpdateCount < 60 &&
      current.state.data?.pages.some((page) =>
        page.items.some((photo) => ["PENDING", "PROCESSING"].includes(photo.state)),
      )
        ? 5000
        : false,
  });
  const refresh = useCallback(() => {
    void queries.invalidateQueries({ queryKey: ["occasion-album", account.id, occasionId] });
    void queries.invalidateQueries({ queryKey: ["album-sources", account.id, occasionId] });
  }, [queries, account.id, occasionId]);
  const reserved = useCallback((key: string, assetId: string) => {
    setSelected((items) => items.map((item) => (item.key === key ? { ...item, assetId } : item)));
  }, []);
  const finished = useCallback(
    (key: string) => {
      setSelected((items) => items.filter((item) => item.key !== key));
      refresh();
    },
    [refresh],
  );
  const photos = [
    ...new Map(
      query.data?.pages.flatMap((page) => page.items).map((photo) => [photo.assetId, photo]),
    ).values(),
  ].filter((photo) => !selected.some((item) => item.assetId === photo.assetId));
  function choose(files: FileList | null) {
    const accepted: SelectedPhoto[] = [];
    const errors: string[] = [];
    for (const file of Array.from(files ?? [])) {
      try {
        photoType(file);
        if (selected.length + accepted.length >= 24)
          throw new Error("Choose at most 24 photos at a time.");
        accepted.push({ key: crypto.randomUUID(), file });
      } catch (failure) {
        errors.push(failure instanceof Error ? failure.message : "Choose another photo.");
      }
    }
    setSelected((items) => [...items, ...accepted]);
    setSelectionError([...new Set(errors)].join(" "));
  }
  if (ended) return null;
  return (
    <section className="entry-photos occasion-album" aria-labelledby={`${id}-title`}>
      <div className="photo-heading">
        <h2 id={`${id}-title`}>Memories from this occasion</h2>
        <button type="button" className="text-button" onClick={refresh}>
          Reload album
        </button>
      </div>
      <p className="form-footnote">
        One album for the whole occasion, including photos from its wine entries. Only you can see
        it.
      </p>
      <div className="form-field photo-picker">
        <label htmlFor={`${id}-files`}>Add occasion photos</label>
        <input
          id={`${id}-files`}
          type="file"
          accept={PHOTO_ACCEPT}
          multiple
          disabled={query.isPending || Boolean(query.error)}
          onChange={(event) => {
            choose(event.target.files);
            event.target.value = "";
          }}
          aria-describedby={`${id}-formats`}
        />
        <p id={`${id}-formats`} className="form-footnote">
          JPEG, PNG, WebP or HEIC, up to 20 MB each. Add up to 24 photos directly to this occasion.
        </p>
      </div>
      {selectionError && (
        <p className="form-message" role="alert">
          {selectionError}
        </p>
      )}
      {selected.length > 0 && (
        <>
          <p className="form-footnote">
            Keep this page open until uploads finish. Selected files aren’t kept after a reload.
          </p>
          <ul className="photo-selections">
            {selected.map((photo) => (
              <PhotoSelection
                key={photo.key}
                photo={photo}
                occasionId={occasionId}
                api={api}
                onAsset={reserved}
                onDone={finished}
              />
            ))}
          </ul>
        </>
      )}
      {query.isPending && <p role="status">Opening your album…</p>}
      {query.error && <JournalError error={query.error} retry={refresh} />}
      {!query.isPending && !query.error && !photos.length && !selected.length && (
        <p className="photo-empty">
          The table, the people, the little details. Add a photo to start this album.
        </p>
      )}
      {photos.length > 0 && (
        <>
          <p className="list-order">Newest photos added first</p>
          <ul className="photo-gallery">
            {photos.map((photo) => {
              const source = photo.source;
              const sources = (
                <AlbumSources
                  occasionId={occasionId}
                  assetId={photo.assetId}
                  count={photo.sourceCount}
                />
              );
              return source.kind === "OCCASION" ? (
                <PhotoCard
                  key={photo.assetId}
                  api={api}
                  refresh={refresh}
                  photo={{ ...photo, occasionId, caption: source.caption, version: source.version }}
                >
                  {sources}
                </PhotoCard>
              ) : (
                <li className="photo-card" key={photo.assetId} data-testid="inherited-photo">
                  <PhotoFrame api={api} photo={{ ...photo, caption: source.caption }} />
                  {source.caption && <p className="album-caption">{source.caption}</p>}
                  <Link
                    className="album-entry-link"
                    href={`/my-wines/${source.userWineId}?entry=${source.parentId}#history-title`}
                    prefetch={false}
                  >
                    From a wine entry · View wine
                  </Link>
                  {sources}
                </li>
              );
            })}
          </ul>
        </>
      )}
      {query.hasNextPage && (
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
