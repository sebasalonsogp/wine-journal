"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { privateResetEvent } from "@/lib/session/private-drafts";
import { usePendingImages } from "./use-pending-images";
import { PhotoCard } from "./photo-card";
import { PhotoSelection, type SelectedPhoto } from "./photo-selection";
import {
  PHOTO_ACCEPT,
  photoFailure,
  photoType,
  type EntryPhoto,
  type PhotoApi,
} from "./photo-upload";

export function PhotoWorkspace({
  api,
  entryId,
  onSelectionChange,
}: {
  api: PhotoApi;
  entryId?: string;
  onSelectionChange?: (count: number) => void;
}) {
  const id = useId();
  const [selected, setSelected] = useState<SelectedPhoto[]>([]);
  const [photos, setPhotos] = useState<EntryPhoto[]>([]);
  const [loading, setLoading] = useState(Boolean(entryId));
  const [error, setError] = useState("");
  const [selectionError, setSelectionError] = useState("");
  const [revision, setRevision] = useState(0);
  const [ended, setEnded] = useState(false);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
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

  useEffect(() => {
    onSelectionChange?.(selected.length);
  }, [onSelectionChange, selected.length]);
  useEffect(() => {
    const reset = () => {
      setEnded(true);
      setSelected([]);
      setPhotos([]);
    };
    window.addEventListener(privateResetEvent, reset);
    return () => window.removeEventListener(privateResetEvent, reset);
  }, []);
  usePendingImages(selected.length > 0);

  useEffect(() => {
    if (!entryId || ended) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let polls = 0;
    async function load() {
      try {
        const result = await api.call((client, timeout) =>
          client.GET("/api/v1/entries/{entry_id}/photos", {
            params: { path: { entry_id: entryId! } },
            signal: AbortSignal.any([controller.signal, timeout]),
          }),
        );
        if (controller.signal.aborted) return;
        setPhotos(result.items);
        setError("");
        if (
          ++polls < 60 &&
          result.items.some((photo) => ["PENDING", "PROCESSING"].includes(photo.state))
        )
          timer = setTimeout(() => void load(), 5000);
      } catch (failure) {
        if (!controller.signal.aborted) setError(photoFailure(failure));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [api, entryId, revision, ended]);

  const visible = photos.filter(
    (photo) => !selected.some((item) => item.assetId === photo.assetId),
  );
  function choose(files: FileList | null) {
    if (!files) return;
    const accepted: SelectedPhoto[] = [];
    const errors: string[] = [];
    for (const file of Array.from(files)) {
      try {
        photoType(file);
        if (visible.length + selected.length + accepted.length >= 12)
          throw new Error("Choose at most 12 photos per entry.");
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
    <section className="entry-photos" aria-labelledby={`${id}-title`}>
      <div className="photo-heading">
        <h2 id={`${id}-title`}>Photos & memories</h2>
        {entryId && (
          <button type="button" className="text-button" onClick={refresh}>
            Reload photos
          </button>
        )}
      </div>
      <p className="form-footnote">
        Private moments from this entry. JPEG, PNG, WebP or HEIC, up to 20 MB each.
      </p>
      {!entryId && (
        <p className="form-footnote">
          Choose photos now; they’ll upload after you save the wine and date.
        </p>
      )}
      <div className="form-field photo-picker">
        <label htmlFor={`${id}-files`}>Add photos</label>
        <input
          id={`${id}-files`}
          type="file"
          accept={PHOTO_ACCEPT}
          multiple
          disabled={Boolean(entryId) && (loading || Boolean(error))}
          onChange={(event) => {
            choose(event.target.files);
            event.target.value = "";
          }}
        />
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
                entryId={entryId}
                api={api}
                onAsset={reserved}
                onDone={finished}
              />
            ))}
          </ul>
        </>
      )}
      {loading && <p role="status">Opening photos…</p>}
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && !visible.length && !selected.length && (
        <p className="photo-empty">A label, a table, a moment. Add a photo whenever you like.</p>
      )}
      {visible.length > 0 && (
        <ul className="photo-gallery">
          {visible.map((photo) => (
            <PhotoCard key={photo.assetId} photo={photo} api={api} refresh={refresh} />
          ))}
        </ul>
      )}
    </section>
  );
}

export function EntryPhotos({ api, entryId }: { api: PhotoApi; entryId: string }) {
  const [opened, setOpened] = useState(false);
  return (
    <details
      className="entry-photo-disclosure"
      onToggle={(event) => {
        if (event.currentTarget.open) setOpened(true);
      }}
    >
      <summary>Photos & memories</summary>
      {opened && <PhotoWorkspace api={api} entryId={entryId} />}
    </details>
  );
}
